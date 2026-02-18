"""Unit tests for ScheduleJobTool.

TDD approach: test with mocked dependencies.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cron.models import Job
from src.cron.scheduler import CronScheduler
from src.tools.schedule_job import ScheduleJobParams, ScheduleJobTool


@pytest.fixture
def mock_scheduler():
    """Create mocked CronScheduler."""
    scheduler = MagicMock(spec=CronScheduler)
    scheduler.submit_user_job = AsyncMock(return_value="test-job-id")
    return scheduler


@pytest.fixture
def tool(mock_scheduler):
    """Create ScheduleJobTool with mocked scheduler."""
    return ScheduleJobTool(scheduler=mock_scheduler)


class TestScheduleJobToolUnit:
    """Unit tests with mocked dependencies."""

    async def test_valid_cron_creates_job(self, tool, mock_scheduler):
        """Valid cron expression submits job for approval."""
        params = ScheduleJobParams(
            name="Daily Report",
            description="Send daily summary",
            cron_expression="0 9 * * *",
        )

        result = await tool.execute(params)

        assert mock_scheduler.submit_user_job.called
        call_args = mock_scheduler.submit_user_job.call_args[1]
        assert call_args["name"] == "Daily Report"
        assert call_args["expression"] == "0 9 * * *"
        assert "approval" in result.output.lower()

    async def test_invalid_cron_returns_error(self, tool, mock_scheduler):
        """Invalid cron expression returns error."""
        params = ScheduleJobParams(
            name="Bad Job",
            description="This won't work",
            cron_expression="invalid cron",
        )

        result = await tool.execute(params)

        assert result.error is not None
        assert "invalid" in result.error.lower()
        assert not mock_scheduler.submit_user_job.called

    async def test_custom_code_used_when_provided(self, tool, mock_scheduler):
        """User-provided code is used instead of generated."""
        custom_code = "async def run(): print('custom')"
        params = ScheduleJobParams(
            name="Custom Job",
            description="Do something",
            cron_expression="*/5 * * * *",
            code=custom_code,
        )

        await tool.execute(params)

        call_args = mock_scheduler.submit_user_job.call_args[1]
        assert call_args["code"] == custom_code

    async def test_code_generated_when_not_provided(self, tool, mock_scheduler):
        """Code is auto-generated from description."""
        params = ScheduleJobParams(
            name="Auto Job",
            description="Send notification",
            cron_expression="0 12 * * *",
        )

        await tool.execute(params)

        call_args = mock_scheduler.submit_user_job.call_args[1]
        assert "async def run()" in call_args["code"]
        assert "Send notification" in call_args["code"]

    async def test_returns_job_id_in_output(self, tool, mock_scheduler):
        """Result includes job ID for approval."""
        mock_scheduler.submit_user_job.return_value = "abc-123-xyz"

        params = ScheduleJobParams(
            name="Test Job",
            description="Test",
            cron_expression="* * * * *",
        )

        result = await tool.execute(params)

        assert "abc-123-xyz" in result.output

    async def test_every_minute_cron_accepted(self, tool, mock_scheduler):
        """'* * * * *' is valid."""
        params = ScheduleJobParams(
            name="Frequent Job",
            description="Run every minute",
            cron_expression="* * * * *",
        )

        result = await tool.execute(params)

        assert result.error is None
        assert mock_scheduler.submit_user_job.called


class TestScheduleJobToolValidation:
    """Tests for parameter validation."""

    def test_empty_name_rejected(self):
        """Empty job name fails validation."""
        with pytest.raises(ValueError):
            ScheduleJobParams(
                name="",
                description="Test",
                cron_expression="* * * * *",
            )

    def test_empty_description_rejected(self):
        """Empty description fails validation."""
        with pytest.raises(ValueError):
            ScheduleJobParams(
                name="Test",
                description="",
                cron_expression="* * * * *",
            )

    def test_whitespace_only_name_rejected(self):
        """Whitespace-only name fails validation."""
        with pytest.raises(ValueError):
            ScheduleJobParams(
                name="   ",
                description="Test",
                cron_expression="* * * * *",
            )
