"""Tests for cron expression parser utility functions.

TDD approach: write tests first, then implement to make them pass.
"""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from src.cron.parser import get_next_run, is_valid, should_run


class TestIsValid:
    """Tests for is_valid() function."""

    def test_valid_basic_expressions(self):
        """Standard cron expressions should be valid."""
        valid_expressions = [
            "* * * * *",        # Every minute
            "*/5 * * * *",      # Every 5 minutes
            "0 * * * *",        # Every hour
            "0 0 * * *",        # Daily at midnight
            "0 19 * * 0",       # Sunday at 7pm
            "0 9 * * 1-5",      # Weekdays at 9am
            "0,30 * * * *",     # At :00 and :30
            "0 9,12,17 * * *",  # At 9am, 12pm, 5pm
            "0 0 1 * *",        # First of month
            "0 0 31 12 *",      # New Year's Eve
            "59 23 * * *",      # Last minute of day
        ]
        for expr in valid_expressions:
            assert is_valid(expr), f"'{expr}' should be valid"

    def test_invalid_expressions(self):
        """Malformed expressions should be invalid."""
        invalid_expressions = [
            "",                 # Empty string
            "* * * *",          # Missing field
            "* * * * * *",      # Extra field
            "60 * * * *",       # Invalid minute
            "* 24 * * *",       # Invalid hour
            "* * 32 * *",       # Invalid day
            "* * * 13 *",       # Invalid month
            "* * * * 8",        # Invalid day of week
            "abc * * * *",      # Non-numeric
        ]
        for expr in invalid_expressions:
            assert not is_valid(expr), f"'{expr}' should be invalid"


class TestGetNextRun:
    """Tests for get_next_run() function."""

    def test_every_minute(self):
        """* * * * * returns next minute."""
        from_time = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        result = get_next_run("* * * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 10, 31, 0, tzinfo=timezone.utc)

    def test_every_5_minutes(self):
        """*/5 * * * * returns next 5-minute boundary."""
        from_time = datetime(2026, 2, 18, 10, 32, 0, tzinfo=timezone.utc)
        result = get_next_run("*/5 * * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 10, 35, 0, tzinfo=timezone.utc)

    def test_every_hour(self):
        """0 * * * * returns next hour."""
        from_time = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        result = get_next_run("0 * * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 11, 0, 0, tzinfo=timezone.utc)

    def test_daily_at_time(self):
        """0 19 * * * returns next 7pm."""
        from_time = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 19 * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 19, 0, 0, tzinfo=timezone.utc)

    def test_daily_next_day(self):
        """0 19 * * * returns tomorrow if already past 7pm."""
        from_time = datetime(2026, 2, 18, 20, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 19 * * *", from_time)
        
        assert result == datetime(2026, 2, 19, 19, 0, 0, tzinfo=timezone.utc)

    def test_weekly_sunday(self):
        """0 19 * * 0 returns next Sunday at 7pm."""
        # Wednesday Feb 18, 2026
        from_time = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 19 * * 0", from_time)
        
        # Sunday Feb 22, 2026
        assert result == datetime(2026, 2, 22, 19, 0, 0, tzinfo=timezone.utc)

    def test_weekdays(self):
        """0 9 * * 1-5 returns next weekday at 9am."""
        # Saturday Feb 21, 2026
        from_time = datetime(2026, 2, 21, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 9 * * 1-5", from_time)
        
        # Monday Feb 23, 2026
        assert result == datetime(2026, 2, 23, 9, 0, 0, tzinfo=timezone.utc)

    def test_list_of_minutes(self):
        """0,30 * * * * returns next :00 or :30."""
        from_time = datetime(2026, 2, 18, 10, 15, 0, tzinfo=timezone.utc)
        result = get_next_run("0,30 * * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)

    def test_crosses_hour_boundary(self):
        """0,30 * * * * crosses to next hour correctly."""
        from_time = datetime(2026, 2, 18, 10, 45, 0, tzinfo=timezone.utc)
        result = get_next_run("0,30 * * * *", from_time)
        
        assert result == datetime(2026, 2, 18, 11, 0, 0, tzinfo=timezone.utc)

    def test_monthly(self):
        """0 0 1 * * returns first of next month."""
        from_time = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 0 1 * *", from_time)
        
        assert result == datetime(2026, 3, 1, 0, 0, 0, tzinfo=timezone.utc)

    def test_year_boundary(self):
        """0 0 31 12 * handles year boundary."""
        from_time = datetime(2026, 12, 31, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 0 31 12 *", from_time)
        
        assert result == datetime(2027, 12, 31, 0, 0, 0, tzinfo=timezone.utc)

    def test_leap_year_feb_29(self):
        """0 0 29 2 * handles Feb 29 in leap year."""
        # 2028 is a leap year
        from_time = datetime(2028, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 0 29 2 *", from_time)
        
        assert result == datetime(2028, 2, 29, 0, 0, 0, tzinfo=timezone.utc)

    def test_default_from_time(self):
        """Uses current time when from_time not provided."""
        before = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        result = get_next_run("* * * * *")
        after = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        
        # Result should be within 1-2 minutes of now
        assert before <= result <= after + timedelta(minutes=2)

    def test_with_timezone(self):
        """Respects timezone for local execution."""
        from_time = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        result = get_next_run("0 9 * * *", from_time, timezone="America/New_York")
        
        # Should return 9am in America/New_York timezone
        # (which is 14:00 UTC, but we return local time)
        assert result.hour == 9
        assert result.tzinfo == ZoneInfo("America/New_York")
        
        # Verify it's the correct UTC equivalent (next day since 10am UTC > 9am NY)
        # 10am UTC = 5am NY, so next 9am NY is today at 9am (14:00 UTC)
        result_utc = result.astimezone(timezone.utc)
        assert result_utc.hour == 14
        assert result_utc.day == 18

    def test_invalid_expression_raises(self):
        """Invalid expression raises ValueError."""
        with pytest.raises(ValueError):
            get_next_run("invalid * * * *")


class TestShouldRun:
    """Tests for should_run() function."""

    def test_should_run_exact_match(self):
        """Returns True when current time matches schedule since last run."""
        # Every 5 minutes, last ran at 10:30, now 10:35
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 35, 0, tzinfo=timezone.utc)
        
        result = should_run("*/5 * * * *", last_run, current)
        
        assert result is True

    def test_should_not_run_yet(self):
        """Returns False when not yet time to run."""
        # Every 5 minutes, last ran at 10:30, now 10:33
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 33, 0, tzinfo=timezone.utc)
        
        result = should_run("*/5 * * * *", last_run, current)
        
        assert result is False

    def test_should_run_multiple_intervals_missed(self):
        """Returns True if multiple intervals passed (job was missed)."""
        # Every 5 minutes, last ran at 10:30, now 10:45 (15 min gap)
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 45, 0, tzinfo=timezone.utc)
        
        result = should_run("*/5 * * * *", last_run, current)
        
        assert result is True

    def test_should_run_same_minute_boundary(self):
        """Returns True at exact minute boundary."""
        # Every minute, last ran at 10:30:00, now 10:31:00
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 31, 0, tzinfo=timezone.utc)
        
        result = should_run("* * * * *", last_run, current)
        
        assert result is True

    def test_should_not_run_within_same_minute(self):
        """Returns False if within same minute but seconds passed."""
        # Every minute, last ran at 10:30:00, now 10:30:45
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 30, 45, tzinfo=timezone.utc)
        
        result = should_run("* * * * *", last_run, current)
        
        assert result is False

    def test_daily_should_run(self):
        """Daily job should run at scheduled time."""
        # Daily at 9am, last ran yesterday, now 9am today
        last_run = datetime(2026, 2, 17, 9, 0, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 9, 0, 0, tzinfo=timezone.utc)
        
        result = should_run("0 9 * * *", last_run, current)
        
        assert result is True

    def test_daily_should_run_missed_window(self):
        """Daily job should run if scheduled time was missed."""
        # Daily at 9am, last ran yesterday at 9am, now 10am today
        # The 9am window today was missed, so should_run returns True
        last_run = datetime(2026, 2, 17, 9, 0, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        
        result = should_run("0 9 * * *", last_run, current)
        
        # Should be True - we missed the 9am window and need to catch up
        assert result is True

    def test_daily_should_not_run_already_ran(self):
        """Daily job should not run if already ran today."""
        # Daily at 9am, already ran today at 9am, now 10am
        last_run = datetime(2026, 2, 18, 9, 0, 0, tzinfo=timezone.utc)
        current = datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)
        
        result = should_run("0 9 * * *", last_run, current)
        
        # Should be False - already ran at 9am today
        assert result is False
