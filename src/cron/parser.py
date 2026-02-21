"""Cron expression parser utility functions.

Thin wrapper around croniter for parsing standard cron expressions.
All functions are stateless utilities.
"""

from datetime import UTC, datetime
from typing import cast
from zoneinfo import ZoneInfo

from croniter import CroniterBadCronError, croniter  # type: ignore[import-untyped]


def is_valid(expression: str) -> bool:
    """Validate if a string is a valid cron expression.

    Args:
        expression: Cron expression like "*/5 * * * *"

    Returns:
        True if valid, False otherwise
    """
    if not expression or not isinstance(expression, str):
        return False

    # Must have exactly 5 fields (minute hour day month dow)
    fields = expression.split()
    if len(fields) != 5:
        return False

    try:
        croniter(expression)
        return True
    except (CroniterBadCronError, ValueError):
        return False


def get_next_run(
    expression: str,
    from_time: datetime | None = None,
    timezone: str = "UTC",
) -> datetime:
    """Get the next execution time for a cron expression.

    Args:
        expression: Cron expression like "*/5 * * * *"
        from_time: Calculate next run from this time (default: now)
        timezone: Timezone name like "America/New_York" or "UTC"

    Returns:
        Timezone-aware datetime of next execution

    Raises:
        ValueError: If expression is invalid
    """
    if not is_valid(expression):
        raise ValueError(f"Invalid cron expression: {expression}")

    # Use provided time or current time
    if from_time is None:
        from_time = datetime.now(UTC)

    # Ensure from_time is timezone-aware
    if from_time.tzinfo is None:
        from_time = from_time.replace(tzinfo=UTC)

    # Convert from_time to target timezone for calculation
    # This ensures cron schedules are interpreted in local time
    target_tz = ZoneInfo(timezone)
    from_time_local = from_time.astimezone(target_tz)

    # Calculate next run in local time
    itr = croniter(expression, from_time_local)
    next_run_local = cast(datetime, itr.get_next(datetime))

    # Return in target timezone
    return next_run_local.replace(tzinfo=target_tz)


def should_run(
    expression: str,
    last_run: datetime,
    current_time: datetime,
) -> bool:
    """Check if a job should run based on last execution time.

    Args:
        expression: Cron expression
        last_run: When job last executed
        current_time: Current time to check

    Returns:
        True if job should run (schedule matched since last_run)

    Raises:
        ValueError: If expression is invalid
    """
    if not is_valid(expression):
        raise ValueError(f"Invalid cron expression: {expression}")

    # Ensure both times are timezone-aware
    if last_run.tzinfo is None:
        last_run = last_run.replace(tzinfo=UTC)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=UTC)

    # Convert both to UTC for comparison
    current_utc = current_time.astimezone(UTC)
    last_run_utc = last_run.astimezone(UTC)

    # Get all scheduled times between last_run and current_time
    itr = croniter(expression, last_run_utc)

    # Get the next scheduled time strictly after last_run
    # We add 1 minute to last_run to ensure we don't get the same time back
    next_scheduled = cast(datetime, itr.get_next(datetime))

    # Check if there's a scheduled time between last_run and current_time
    # We use minute precision: if next_scheduled <= current_time (at minute boundary)
    next_scheduled_minute = next_scheduled.replace(second=0, microsecond=0)
    current_minute = current_utc.replace(second=0, microsecond=0)
    last_run_minute = last_run_utc.replace(second=0, microsecond=0)

    # Should run if:
    # 1. There's a scheduled time <= current time
    # 2. That scheduled time is strictly after the last run minute
    result: bool = (
        next_scheduled_minute <= current_minute and next_scheduled_minute > last_run_minute
    )
    return result
