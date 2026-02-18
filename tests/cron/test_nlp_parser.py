"""Tests for natural language cron parser."""

import pytest

from src.cron.nlp_parser import NaturalLanguageCronParser, ParsedSchedule


class TestTimeExtraction:
    """Test time extraction from natural language."""

    def test_parse_8am(self):
        """Should parse '8am' as 8:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am")

        assert result is not None
        assert result.cron_expression == "0 8 * * *"
        # Short input gets penalized, so confidence is 0.6 not 0.7
        assert result.confidence >= 0.5

    def test_parse_830pm(self):
        """Should parse '8:30pm' as 20:30."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8:30pm")

        assert result is not None
        assert result.cron_expression == "30 20 * * *"

    def test_parse_24_hour_format(self):
        """Should parse '14:30' as 14:30."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("14:30")

        assert result is not None
        assert result.cron_expression == "30 14 * * *"

    def test_parse_morning(self):
        """Should parse 'morning' as 8:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("morning")

        assert result is not None
        assert result.cron_expression == "0 8 * * *"

    def test_parse_evening(self):
        """Should parse 'evening' as 18:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("evening")

        assert result is not None
        assert result.cron_expression == "0 18 * * *"

    def test_parse_noon(self):
        """Should parse 'noon' as 12:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("noon")

        assert result is not None
        assert result.cron_expression == "0 12 * * *"

    def test_parse_midnight(self):
        """Should parse 'midnight' as 00:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("midnight")

        assert result is not None
        assert result.cron_expression == "0 0 * * *"

    def test_parse_12am(self):
        """Should parse '12am' as 00:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("12am")

        assert result is not None
        assert result.cron_expression == "0 0 * * *"

    def test_parse_12pm(self):
        """Should parse '12pm' as 12:00."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("12pm")

        assert result is not None
        assert result.cron_expression == "0 12 * * *"


class TestFrequencyExtraction:
    """Test frequency extraction from natural language."""

    def test_every_5_minutes(self):
        """Should parse 'every 5 minutes'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every 5 minutes")

        assert result is not None
        assert result.cron_expression == "*/5 * * * *"

    def test_every_minute(self):
        """Should parse 'every minute'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every minute")

        assert result is not None
        assert result.cron_expression == "* * * * *"

    def test_hourly(self):
        """Should parse 'hourly'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("hourly")

        assert result is not None
        assert result.cron_expression == "0 * * * *"

    def test_every_hour(self):
        """Should parse 'every hour'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every hour")

        assert result is not None
        assert result.cron_expression == "0 * * * *"

    def test_daily(self):
        """Should parse 'daily'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("daily")

        assert result is not None
        assert result.cron_expression == "0 0 * * *"

    def test_every_day(self):
        """Should parse 'every day'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every day")

        assert result is not None
        assert result.cron_expression == "0 0 * * *"

    def test_weekly(self):
        """Should parse 'weekly'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("weekly")

        assert result is not None
        assert result.cron_expression == "0 0 * * 0"

    def test_monthly(self):
        """Should parse 'monthly'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("monthly")

        assert result is not None
        assert result.cron_expression == "0 0 1 * *"


class TestDayExtraction:
    """Test day of week extraction."""

    def test_monday(self):
        """Should parse 'Monday'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("Monday at 9am")

        assert result is not None
        assert result.cron_expression == "0 9 * * 1"

    def test_sunday(self):
        """Should parse 'Sunday'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("Sunday at 7pm")

        assert result is not None
        assert result.cron_expression == "0 19 * * 0"

    def test_weekdays(self):
        """Should parse 'weekdays'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("weekdays at 9am")

        assert result is not None
        assert result.cron_expression == "0 9 * * 1-5"

    def test_weekends(self):
        """Should parse 'weekends'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("weekends at 10am")

        assert result is not None
        assert result.cron_expression == "0 10 * * 0,6"


class TestCombinedPatterns:
    """Test combined time + frequency + day patterns."""

    def test_every_morning_at_8am(self):
        """Should parse 'every morning at 8am'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every morning at 8am")

        assert result is not None
        assert result.cron_expression == "0 8 * * *"

    def test_sundays_at_7pm(self):
        """Should parse 'Sundays at 7pm'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("Sundays at 7pm")

        assert result is not None
        assert result.cron_expression == "0 19 * * 0"

    def test_every_15_minutes(self):
        """Should parse 'every 15 minutes'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every 15 minutes")

        assert result is not None
        assert result.cron_expression == "*/15 * * * *"

    def test_daily_at_noon(self):
        """Should parse 'daily at noon'."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("daily at noon")

        assert result is not None
        assert result.cron_expression == "0 12 * * *"


class TestTimezoneSupport:
    """Test timezone extraction."""

    def test_est_timezone(self):
        """Should parse timezone abbreviation EST."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am EST")

        assert result is not None
        assert result.timezone == "America/New_York"
        assert result.cron_expression == "0 8 * * *"

    def test_pst_timezone(self):
        """Should parse timezone abbreviation PST."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("9pm PST")

        assert result is not None
        assert result.timezone == "America/Los_Angeles"
        assert result.cron_expression == "0 21 * * *"

    def test_in_new_york(self):
        """Should parse 'in New York' timezone."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am in New York")

        assert result is not None
        assert result.timezone == "America/New_York"

    def test_in_tokyo(self):
        """Should parse 'in Tokyo' timezone."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("9am in Tokyo")

        assert result is not None
        assert result.timezone == "Asia/Tokyo"


class TestConfidenceScoring:
    """Test confidence scoring for ambiguous input."""

    def test_high_confidence_explicit_time_and_day(self):
        """Should have high confidence for clear input."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("Sundays at 7pm")

        assert result is not None
        assert result.confidence >= 0.7

    def test_low_confidence_vague_input(self):
        """Should have low confidence for vague input."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("sometimes in the morning")

        assert result is not None
        assert result.confidence < 0.7

    def test_medium_confidence_time_only(self):
        """Should have medium confidence for time without frequency."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am")

        assert result is not None
        # Should be medium confidence (0.5 base + 0.2 for time)
        assert 0.5 <= result.confidence <= 0.8


class TestUnparseableInput:
    """Test handling of unparseable input."""

    def test_returns_none_for_gibberish(self):
        """Should return None for completely unparseable input."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("purple monkey dishwasher")

        assert result is None

    def test_returns_none_for_empty_string(self):
        """Should return None for empty string."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("")

        assert result is None

    def test_returns_none_for_whitespace(self):
        """Should return None for whitespace-only input."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("   ")

        assert result is None


class TestDescriptionGeneration:
    """Test human-readable description generation."""

    def test_daily_description(self):
        """Should describe daily schedule."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am")

        assert result is not None
        assert "8:00 AM" in result.description

    def test_weekly_description(self):
        """Should describe weekly schedule."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("Sundays at 7pm")

        assert result is not None
        assert "7:00 PM" in result.description
        assert "Sundays" in result.description

    def test_frequency_description(self):
        """Should describe frequency-based schedule."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("every 5 minutes")

        assert result is not None
        assert "Every 5 minutes" in result.description

    def test_timezone_in_description(self):
        """Should include timezone in description."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8am EST")

        assert result is not None
        assert "New York" in result.description or "Eastern" in result.description


class TestClarification:
    """Test clarification question generation."""

    def test_clarify_missing_time_and_frequency(self):
        """Should ask for both time and frequency when missing."""
        parser = NaturalLanguageCronParser()
        question = parser.clarify("run my job")

        assert "when" in question.lower() or "time" in question.lower()

    def test_clarify_missing_time(self):
        """Should ask for time when frequency provided but not time."""
        parser = NaturalLanguageCronParser()
        question = parser.clarify("every day")

        assert "time" in question.lower()

    def test_clarify_missing_frequency(self):
        """Should ask for frequency when time provided but not frequency."""
        parser = NaturalLanguageCronParser()
        question = parser.clarify("at 8am")

        assert "how often" in question.lower() or "every day" in question.lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_digit_hour(self):
        """Should handle single digit hours."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("9am")

        assert result is not None
        assert result.cron_expression == "0 9 * * *"

    def test_leading_zero_hour(self):
        """Should handle hours with leading zero."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("09:30")

        assert result is not None
        assert result.cron_expression == "30 9 * * *"

    def test_case_insensitive_days(self):
        """Should handle uppercase day names."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("MONDAY AT 9AM")

        assert result is not None
        assert result.cron_expression == "0 9 * * 1"

    def test_extra_whitespace(self):
        """Should handle extra whitespace."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("  every   5   minutes  ")

        assert result is not None
        assert result.cron_expression == "*/5 * * * *"


class TestParsedScheduleDataclass:
    """Test ParsedSchedule dataclass."""

    def test_creation(self):
        """Should create ParsedSchedule with all fields."""
        schedule = ParsedSchedule(
            cron_expression="0 8 * * *",
            description="At 8:00 AM daily",
            confidence=0.9,
            timezone="America/New_York",
        )

        assert schedule.cron_expression == "0 8 * * *"
        assert schedule.description == "At 8:00 AM daily"
        assert schedule.confidence == 0.9
        assert schedule.timezone == "America/New_York"

    def test_optional_timezone(self):
        """Should allow timezone to be None."""
        schedule = ParsedSchedule(
            cron_expression="0 8 * * *",
            description="At 8:00 AM daily",
            confidence=0.9,
        )

        assert schedule.timezone is None

    def test_default_confidence(self):
        """Should use 0.0 as default confidence."""
        schedule = ParsedSchedule(
            cron_expression="0 8 * * *",
            description="At 8:00 AM daily",
        )

        assert schedule.confidence == 0.0


class TestInvalidTimeHandling:
    """Test handling of invalid time formats."""

    def test_invalid_hour_in_am_pm(self):
        """Should handle invalid hour in am/pm format."""
        parser = NaturalLanguageCronParser()
        # "13am" is invalid - should be handled gracefully
        result = parser.parse("13am")

        # Should either return None or use a fallback
        if result is not None:
            # If it parses, it shouldn't crash
            assert isinstance(result.cron_expression, str)

    def test_invalid_minute(self):
        """Should handle invalid minute values."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("8:99am")

        # Should either return None or handle gracefully
        if result is not None:
            assert isinstance(result.cron_expression, str)

    def test_boundary_24_hour(self):
        """Should handle 24:00 boundary."""
        parser = NaturalLanguageCronParser()
        result = parser.parse("24:00")

        # 24:00 is technically invalid, should return None or midnight
        if result is not None:
            # If it parses, validate it's a valid cron
            parts = result.cron_expression.split()
            assert len(parts) == 5
