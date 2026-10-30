"""Smoke tests for the Week 1 skeleton.

These exist so CI has a real test to run before any feature code is written.
Replace or extend them as services are built.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    "CLAUDE.md",
    "README.md",
    "Makefile",
    "pyproject.toml",
    "docs/PROJECT_PLAN.md",
    "docs/LOG.md",
    "docs/product/VISION.md",
    "docs/product/METRICS.md",
    "docs/risk/RISK_REGISTER.md",
    "docs/adr/0001-record-architecture-decisions.md",
    ".github/workflows/ci.yml",
    ".devcontainer/devcontainer.json",
]


def test_required_repo_files_exist() -> None:
    missing = [p for p in REQUIRED_PATHS if not (ROOT / p).is_file()]
    assert missing == []


def test_service_folders_exist() -> None:
    for folder in ["services/api", "services/assistant", "services/mcp_bank", "ml/intent"]:
        assert (ROOT / folder).is_dir(), folder
