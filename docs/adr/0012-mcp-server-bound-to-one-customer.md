# 0012: MCP tool server bound to one customer, on the official SDK (v1)

**Status:** Accepted, 2026-10-29. Decided without the owner, under the instruction to finish what can be finished.

## Context
Plan Week 5 asks for MCP tool calling. The bank tools were a plain Python class. An MCP server lets a model call tools over the protocol, but a model must never be able to choose which customer it acts for.

## Decision
- `services/mcp_bank/mcp_server.py` builds a FastMCP server (MCP SDK v1, pinned `mcp>=1.2,<2`; v2 renamed the API) for ONE customer. The customer is set when the server is built, not by a tool argument.
- Every account, card and transaction is checked against that customer's accounts before the call reaches the tool server. Writes keep the two-step flow and the disputes approval gate.
- Tests run every tool through a real MCP client session (`tests/test_mcp_bank.py`).

## Consequences
- Cross-customer access is refused at the protocol layer as well as in the API.
- The MCP transport is in-process in tests. Serving it over stdio or HTTP to a real client is not run.
