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
    assert "prompt fragment" in guide.lower()
    assert "persistent warning banner" in guide.lower()
    assert "fail closed" in guide.lower()
    assert "manual recovery" in guide.lower()


def test_readme_links_to_template_sync_guide() -> None:
    """README should point readers to the canonical template-sync guide."""
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")

    assert "[Template Sync and Conflict Recovery](docs/template-sync.md)" in readme
    assert "conflict-recovery reference" in readme.lower()


def test_architecture_doc_mentions_workspace_scoped_sync_records_and_blocked_files() -> None:
    """Architecture docs should summarize the final template sync contract."""
    architecture = (PROJECT_ROOT / "docs" / "ARCHITECTURE.md").read_text(encoding="utf-8")

    assert "TemplateManager.reconcile_template()" in architecture
    assert "workspace-scoped" in architecture
    assert "Template Sync and Conflict Recovery" in architecture
    assert "template-sync.md" in architecture
    assert "/context" in architecture
    assert "WebUI" in architecture
    assert "prompt fragments" in architecture.lower()
    assert "warning banner" in architecture.lower()
    assert "blocked" in architecture.lower()
