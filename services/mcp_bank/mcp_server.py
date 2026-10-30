"""MCP server for the bank tools (Week 5, plan: MCP tool calling).

Built on the official MCP Python SDK (v1, FastMCP). The server is bound to ONE customer when it is
created. The customer is never an argument a model can change. Every account, card and transaction
the tools touch is checked against that customer's own accounts before the tool server runs.

Writes keep the two-step flow: `propose_write` returns a token, `confirm_write` executes it.
No tool moves money (ADR 0002). Tests in tests/test_mcp_bank.py exercise this through an MCP client.
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from services.mcp_bank.server import TOOLS, BankToolServer, ToolError
from services.mockbank.bank import MockBank, NotFoundError

WRITE_TOOLS = sorted(name for name, spec in TOOLS.items() if spec.needs_confirmation)


class OwnershipError(PermissionError):
    """The requested account, card or transaction is not the bound customer's."""


def _owned_accounts(bank: MockBank, customer_id: str) -> set[str]:
    return {
        str(a) for a in bank.accounts.loc[bank.accounts["customer_id"] == customer_id, "account_id"]
    }


def _check_account(owned: set[str], account_id: str) -> None:
    if account_id not in owned:
        raise OwnershipError("account does not belong to this customer")


def _check_card(bank: MockBank, owned: set[str], card_id: str) -> None:
    try:
        account = bank.get_card(card_id)["account_id"]
    except NotFoundError as exc:
        raise OwnershipError("card not found") from exc
    if account not in owned:
        raise OwnershipError("card does not belong to this customer")


def _check_txn(bank: MockBank, owned: set[str], txn_id: str) -> None:
    try:
        account = bank.find_transaction(txn_id)["account_id"]
    except NotFoundError as exc:
        raise OwnershipError("transaction not found") from exc
    if account not in owned:
        raise OwnershipError("transaction does not belong to this customer")


def build_server(tools: BankToolServer, customer_id: str, name: str = "meridian-bank") -> FastMCP:
    """One MCP server bound to one customer. Create a new server per customer session."""
    bank = tools.bank
    owned = _owned_accounts(bank, customer_id)
    actor = f"cust-{customer_id}"
    mcp = FastMCP(name)

    @mcp.tool()
    def get_balance(account_id: str) -> dict[str, Any]:
        """Balance of one of the customer's accounts, in fils."""
        _check_account(owned, account_id)
        return tools.call(actor, "get_balance", {"account_id": account_id})

    @mcp.tool()
    def list_transactions(account_id: str, limit: int = 20) -> dict[str, Any]:
        """Recent transactions on one of the customer's accounts, newest first."""
        _check_account(owned, account_id)
        return tools.call(actor, "list_transactions", {"account_id": account_id, "limit": limit})

    @mcp.tool()
    def explain_fee(fee: str) -> dict[str, Any]:
        """Explain a fee type by name, with the policy it comes from."""
        return tools.call(actor, "explain_fee", {"fee": fee})

    @mcp.tool()
    def request_human_agent(summary: str) -> dict[str, Any]:
        """Hand the conversation to a human agent with a short summary."""
        return tools.call(actor, "request_human_agent", {"summary": summary})

    @mcp.tool()
    def propose_write(tool: str, args: dict[str, Any]) -> dict[str, str]:
        """Propose a write (freeze_card, open_dispute, update_address).

        Returns a confirmation token.
        """
        if tool not in WRITE_TOOLS:
            raise ToolError(f"{tool} is not a write tool")
        if tool == "freeze_card":
            _check_card(bank, owned, str(args.get("card_id", "")))
        elif tool == "open_dispute":
            _check_txn(bank, owned, str(args.get("txn_id", "")))
        else:
            if str(args.get("customer_id")) != customer_id:
                raise OwnershipError("address change is only for the bound customer")
        token = tools.propose(actor, tool, args)
        return {"token": token, "tool": tool}

    @mcp.tool()
    def confirm_write(token: str) -> dict[str, Any]:
        """Confirm a proposed write.

        Refused for other sessions and for disputes that need approval.
        """
        return tools.confirm(actor, token)

    return mcp
