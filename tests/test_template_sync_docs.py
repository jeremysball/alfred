from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_template_sync_guide_documents_sync_store_conflicts_and_recovery() -> None:
    """The template sync guide should explain conflict recovery end to end."""
    guide = (PROJECT_ROOT / "docs" / "template-sync.md").read_text(encoding="utf-8")

    assert "XDG_CACHE_HOME/alfred/template-sync.json" in guide
    assert "TemplateManager.reconcile_template()" in guide
    assert "workspace-scoped" in guide
    assert "<<<<<<< ours" in guide
    assert "=======\n" in guide
    assert ">>>>>>> theirs" in guide
    assert "/context" in guide
    assert "WebUI" in guide
    assert "fail closed" in guide.lower()
    assert "manual recovery" in guide.lower()
