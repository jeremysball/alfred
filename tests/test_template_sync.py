"""Tests for template sync metadata contracts."""

from datetime import UTC, datetime
from pathlib import Path

from alfred.template_sync import TemplateBaseSnapshot, TemplateSyncRecord, TemplateSyncState, TemplateSyncStore


def test_template_sync_record_captures_template_workspace_and_base_hashes() -> None:
    """Sync records preserve template, workspace, and base hashes with state."""
    record = TemplateSyncRecord(
        name="SYSTEM.md",
        template_path=Path("/templates/SYSTEM.md"),
        workspace_path=Path("/workspace/SYSTEM.md"),
        template_hash="template-sha",
        workspace_hash="workspace-sha",
        base_hash="base-sha",
        state=TemplateSyncState.CLEAN,
    )

    assert record.name == "SYSTEM.md"
    assert record.template_path == Path("/templates/SYSTEM.md")
    assert record.workspace_path == Path("/workspace/SYSTEM.md")
    assert record.template_hash == "template-sha"
    assert record.workspace_hash == "workspace-sha"
    assert record.base_hash == "base-sha"
    assert record.state is TemplateSyncState.CLEAN


def test_template_sync_store_round_trips_records(tmp_path: Path) -> None:
    """Sync store persists records and reloads them on restart."""
    path = tmp_path / "template-sync.json"
    store = TemplateSyncStore(path)

    record = TemplateSyncRecord(
        name="SYSTEM.md",
        template_path=tmp_path / "templates" / "SYSTEM.md",
        workspace_path=tmp_path / "workspace" / "SYSTEM.md",
        template_hash="template-sha",
        workspace_hash="workspace-sha",
        base_hash="base-sha",
        state=TemplateSyncState.MERGED,
        updated_at=datetime(2026, 3, 22, 12, 0, 0, tzinfo=UTC),
    )

    store.save(record)

    reloaded = TemplateSyncStore(path)

    assert reloaded.get("SYSTEM.md") == record
    assert reloaded.list_records() == [record]
    assert reloaded.path == path


def test_template_sync_state_distinguishes_clean_merged_and_conflicted_records() -> None:
    """Record helpers classify sync states consistently."""
    cases = [
        (TemplateSyncState.CLEAN, True, False, False),
        (TemplateSyncState.MERGED, True, False, False),
        (TemplateSyncState.PENDING, False, True, False),
        (TemplateSyncState.CONFLICTED, False, False, True),
    ]

    for state, is_clean, needs_merge, is_conflicted in cases:
        record = TemplateSyncRecord(
            name="SYSTEM.md",
            template_path=Path("/templates/SYSTEM.md"),
            workspace_path=Path("/workspace/SYSTEM.md"),
            template_hash="template-sha",
            workspace_hash="workspace-sha",
            base_hash="base-sha",
            state=state,
        )

        assert record.is_clean() is is_clean
        assert record.needs_merge() is needs_merge
        assert record.is_conflicted() is is_conflicted


def test_template_sync_record_round_trips_base_snapshot_payload(tmp_path: Path) -> None:
    """Sync records persist the base snapshot payload through the store."""
    path = tmp_path / "template-sync.json"
    store = TemplateSyncStore(path)

    snapshot = TemplateBaseSnapshot(
        content="# System\n\noriginal template body",
        hash="base-snapshot-sha",
        captured_at=datetime(2026, 3, 22, 13, 15, 0, tzinfo=UTC),
    )
    record = TemplateSyncRecord(
        name="SYSTEM.md",
        template_path=tmp_path / "templates" / "SYSTEM.md",
        workspace_path=tmp_path / "workspace" / "SYSTEM.md",
        template_hash="template-sha",
        workspace_hash="workspace-sha",
        base_hash=snapshot.hash,
        base_snapshot=snapshot,
        state=TemplateSyncState.CLEAN,
        updated_at=datetime(2026, 3, 22, 13, 30, 0, tzinfo=UTC),
    )

    store.save(record)

    reloaded = TemplateSyncStore(path)
    reloaded_record = reloaded.get("SYSTEM.md")

    assert reloaded_record is not None
    assert reloaded_record.base_snapshot == snapshot
    assert reloaded_record.base_snapshot.content == snapshot.content
    assert reloaded_record.base_snapshot.hash == snapshot.hash
    assert reloaded_record.base_snapshot.captured_at == snapshot.captured_at
    assert reloaded_record.base_hash == snapshot.hash
