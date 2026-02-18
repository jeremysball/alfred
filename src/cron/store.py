"""Cron job persistence layer.

Handles saving/loading jobs from JSONL files with atomic writes.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from src.cron.models import ExecutionRecord, Job

logger = logging.getLogger(__name__)


class CronStore:
    """Persistent storage for cron jobs and execution history.

    Jobs are stored in data/cron.jsonl (full rewrite on change).
    History is stored in data/cron_history.jsonl (append-only).
    All writes are atomic (temp file + rename).
    """

    def __init__(self, data_dir: Path | str | None = None) -> None:
        """Initialize store with data directory.

        Args:
            data_dir: Directory for JSONL files (default: data/)
        """
        if data_dir is None:
            data_dir = Path("data")
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.jobs_path = self.data_dir / "cron.jsonl"
        self.history_path = self.data_dir / "cron_history.jsonl"

    async def save_job(self, job: Job) -> None:
        """Save job to cron.jsonl.

        Rewrites entire file to ensure consistency.
        Uses atomic write (temp file + rename).

        Args:
            job: Job to save
        """
        # Load existing jobs
        jobs = await self.load_jobs()

        # Update or add job
        jobs_dict = {j.job_id: j for j in jobs}
        job.updated_at = datetime.now(UTC)
        jobs_dict[job.job_id] = job

        # Write all jobs atomically
        await self._write_jobs_atomic(list(jobs_dict.values()))
        logger.debug(f"Saved job: {job.name} ({job.job_id})")

    async def delete_job(self, job_id: str) -> None:
        """Delete job from cron.jsonl.

        Args:
            job_id: ID of job to delete
        """
        jobs = await self.load_jobs()
        jobs = [j for j in jobs if j.job_id != job_id]
        await self._write_jobs_atomic(jobs)
        logger.debug(f"Deleted job: {job_id}")

    async def load_jobs(self) -> list[Job]:
        """Load all jobs from cron.jsonl.

        Returns:
            List of jobs (empty if file doesn't exist)
        """
        if not self.jobs_path.exists():
            return []

        jobs = []
        content = await self._read_file_async(self.jobs_path)

        for line_num, line in enumerate(content.strip().split("\n"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                jobs.append(Job.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping corrupt line {line_num} in {self.jobs_path}: {e}")

        return jobs

    async def record_execution(self, record: ExecutionRecord) -> None:
        """Append execution record to cron_history.jsonl.

        Args:
            record: Execution record to append
        """
        line = json.dumps(record.to_dict()) + "\n"
        await self._append_file_async(self.history_path, line)
        logger.debug(f"Recorded execution: {record.execution_id} for job {record.job_id}")

    async def get_job_history(
        self,
        job_id: str,
        limit: int | None = None,
    ) -> list[ExecutionRecord]:
        """Get execution history for a specific job.

        Args:
            job_id: Job ID to query
            limit: Maximum number of records to return (default: all)

        Returns:
            List of execution records (newest first)
        """
        if not self.history_path.exists():
            return []

        records = []
        content = await self._read_file_async(self.history_path)

        for line in content.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if data.get("job_id") == job_id:
                    records.append(ExecutionRecord.from_dict(data))
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Skipping corrupt history line: {e}")

        # Sort by started_at descending (newest first)
        records.sort(key=lambda r: r.started_at, reverse=True)

        if limit:
            records = records[:limit]

        return records

    async def _write_jobs_atomic(self, jobs: list[Job]) -> None:
        """Write jobs to file atomically using temp file + rename.

        Args:
            jobs: List of jobs to write
        """
        lines = [json.dumps(job.to_dict()) + "\n" for job in jobs]
        temp_path = self.jobs_path.with_suffix(".tmp")

        # Write to temp file
        async with aiofiles.open(temp_path, "w") as f:
            await f.writelines(lines)

        # Atomic rename
        temp_path.rename(self.jobs_path)

    async def _read_file_async(self, path: Path) -> str:
        """Read entire file asynchronously.

        Args:
            path: File path to read

        Returns:
            File contents as string
        """
        if not path.exists():
            return ""
        async with aiofiles.open(path) as f:
            return await f.read()

    async def _append_file_async(self, path: Path, content: str) -> None:
        """Append content to file asynchronously.

        Args:
            path: File path to append to
            content: Content to append
        """
        async with aiofiles.open(path, "a") as f:
            await f.write(content)
