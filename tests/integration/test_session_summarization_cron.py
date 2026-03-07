"""Integration test for cron-based session summarization (slow)."""

import os
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.config import load_config
from src.cron.session_summarizer import summarize_sessions_job
from src.embeddings.openai_provider import OpenAIProvider
from src.session import Message, Role
from src.session_storage import SessionStorage

REQUIRED_ENV_VARS = [
    "TELEGRAM_BOT_TOKEN",
    "OPENAI_API_KEY",
    "KIMI_API_KEY",
    "KIMI_BASE_URL",
]


def _missing_required_env() -> bool:
    return any(not os.environ.get(var) for var in REQUIRED_ENV_VARS)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("SKIP_LLM_TESTS") or _missing_required_env(),
    reason="Requires real LLM and embedding credentials",
)
@pytest.mark.asyncio
async def test_cron_finds_and_summarizes_idle_session(tmp_path: Path, monkeypatch) -> None:
    """Cron job summarizes an idle session and writes summary.json."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    config_dir = Path(os.environ["XDG_CONFIG_HOME"]) / "alfred"
    config_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__).parents[2] / "templates" / "config.toml", config_dir)

    config = load_config()
    config.session_summarize_idle_minutes = 1
    config.session_summarize_message_threshold = 1

    embedder = OpenAIProvider(config)
    storage = SessionStorage(embedder=embedder, data_dir=Path(os.environ["XDG_DATA_HOME"]))

    session_id = "sess_integration"
    meta = storage.create_session(session_id)
    meta.last_active = datetime.now(UTC) - timedelta(minutes=2)
    meta.current_count = 1
    storage.save_meta(meta)

    message = Message(
        idx=0,
        role=Role.USER,
        content="Summarize this session.",
        timestamp=meta.last_active,
        session_id=session_id,
    )
    await storage.append_message(session_id, message)

    summaries_created = await summarize_sessions_job(config, storage, embedder)

    summary_path = storage.sessions_dir / session_id / "summary.json"
    assert summaries_created == 1
    assert summary_path.exists()
    summary_data = summary_path.read_text().strip()
    assert summary_data
