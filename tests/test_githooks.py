"""Tests for repository git hook configuration."""

from pathlib import Path


def test_pre_commit_hook_runs_blocking_mypy_check() -> None:
    """The repository pre-commit hook must fail on mypy errors."""
    hook_path = Path(__file__).parent.parent / ".githooks" / "pre-commit"
    content = hook_path.read_text()

    assert "uv run mypy --strict src/" in content

    mypy_line = next(line for line in content.splitlines() if "mypy" in line and "uv run" in line)
    assert "||" not in mypy_line
    assert "non-blocking" not in mypy_line.lower()
