"""Tests for cron expression parser utility functions.

TDD approach: write tests first, then implement to make them pass.
"""

from datetime import UTC, datetime

from alfred.cron.parser import is_valid, should_run


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

class TestShouldRun:
    """Tests for should_run() function."""

    def test_should_run_exact_match(self):
        """Returns True when current time matches schedule since last run."""
        # Every 5 minutes, last ran at 10:30, now 10:35
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 35, 0, tzinfo=UTC)

        result = should_run("*/5 * * * *", last_run, current)

        assert result is True

    def test_should_not_run_yet(self):
        """Returns False when not yet time to run."""
        # Every 5 minutes, last ran at 10:30, now 10:33
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 33, 0, tzinfo=UTC)

        result = should_run("*/5 * * * *", last_run, current)

        assert result is False

    def test_should_run_multiple_intervals_missed(self):
        """Returns True if multiple intervals passed (job was missed)."""
        # Every 5 minutes, last ran at 10:30, now 10:45 (15 min gap)
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 45, 0, tzinfo=UTC)

        result = should_run("*/5 * * * *", last_run, current)

        assert result is True

    def test_should_run_same_minute_boundary(self):
        """Returns True at exact minute boundary."""
        # Every minute, last ran at 10:30:00, now 10:31:00
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 31, 0, tzinfo=UTC)

        result = should_run("* * * * *", last_run, current)

        assert result is True

    def test_should_not_run_within_same_minute(self):
        """Returns False if within same minute but seconds passed."""
        # Every minute, last ran at 10:30:00, now 10:30:45
        last_run = datetime(2026, 2, 18, 10, 30, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 30, 45, tzinfo=UTC)

        result = should_run("* * * * *", last_run, current)

        assert result is False

    def test_daily_should_run(self):
        """Daily job should run at scheduled time."""
        # Daily at 9am, last ran yesterday, now 9am today
        last_run = datetime(2026, 2, 17, 9, 0, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 9, 0, 0, tzinfo=UTC)

        result = should_run("0 9 * * *", last_run, current)

        assert result is True

    def test_daily_should_run_missed_window(self):
        """Daily job should run if scheduled time was missed."""
        # Daily at 9am, last ran yesterday at 9am, now 10am today
        # The 9am window today was missed, so should_run returns True
        last_run = datetime(2026, 2, 17, 9, 0, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)

        result = should_run("0 9 * * *", last_run, current)

        # Should be True - we missed the 9am window and need to catch up
        assert result is True

    def test_daily_should_not_run_already_ran(self):
        """Daily job should not run if already ran today."""
        # Daily at 9am, already ran today at 9am, now 10am
        last_run = datetime(2026, 2, 18, 9, 0, 0, tzinfo=UTC)
        current = datetime(2026, 2, 18, 10, 0, 0, tzinfo=UTC)

        result = should_run("0 9 * * *", last_run, current)

        # Should be False - already ran at 9am today
        assert result is False
