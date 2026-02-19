"""Natural language to cron expression parser.

Conversational phrases like "every morning at 8am"
into cron expressions with timezone support.
"""

import re
from dataclasses import dataclass


@dataclass
class ParsedSchedule:
    """Result of parsing natural language schedule."""

    cron_expression: str
    description: str
    confidence: float = 0.0  # 0.0-1.0, <0.7 needs clarification
    timezone: str | None = None


class NaturalLanguageCronParser:
    """Parse natural language into cron expressions."""

    # Time-of-day descriptors mapped to (hour, minute)
    # Order matters: longer matches first to avoid "night" matching before "midnight"
    TIME_DESCRIPTORS = {
        "midnight": (0, 0),
        "afternoon": (14, 0),
        "evening": (18, 0),
        "morning": (8, 0),
        "night": (20, 0),
        "noon": (12, 0),
    }

    # Day patterns mapped to cron day-of-week values
    DAY_PATTERNS: dict[str, int | str] = {
        "monday": 1,
        "mon": 1,
        "tuesday": 2,
        "tue": 2,
        "tues": 2,
        "wednesday": 3,
        "wed": 3,
        "thursday": 4,
        "thu": 4,
        "thurs": 4,
        "friday": 5,
        "fri": 5,
        "saturday": 6,
        "sat": 6,
        "sunday": 0,
        "sun": 0,
        "weekday": "1-5",
        "weekdays": "1-5",
        "weekend": "0,6",
        "weekends": "0,6",
    }

    # Common timezone abbreviations and names
    TIMEZONE_ALIASES = {
        "est": "America/New_York",
        "edt": "America/New_York",
        "cst": "America/Chicago",
        "cdt": "America/Chicago",
        "mst": "America/Denver",
        "mdt": "America/Denver",
        "pst": "America/Los_Angeles",
        "pdt": "America/Los_Angeles",
        "gmt": "GMT",
        "utc": "UTC",
        "bst": "Europe/London",
        "cet": "Europe/Berlin",
        "cest": "Europe/Berlin",
        "jst": "Asia/Tokyo",
        "ist": "Asia/Kolkata",
        "aest": "Australia/Sydney",
        "aedt": "Australia/Sydney",
        "new york": "America/New_York",
        "chicago": "America/Chicago",
        "denver": "America/Denver",
        "los angeles": "America/Los_Angeles",
        "london": "Europe/London",
        "paris": "Europe/Paris",
        "berlin": "Europe/Berlin",
        "tokyo": "Asia/Tokyo",
        "sydney": "Australia/Sydney",
    }

    def parse(self, text: str) -> ParsedSchedule | None:
        """Parse natural language into cron expression.

        Args:
            text: Natural language schedule description

        Returns:
            ParsedSchedule if parsed successfully
            None if unable to parse at all
        """
        text_lower = text.lower().strip()

        # Extract timezone first (remove from text for parsing)
        timezone = self._extract_timezone(text_lower)
        text_without_tz = self._remove_timezone(text_lower, timezone)

        # Try to extract components
        time = self._extract_time(text_without_tz)
        frequency = self._extract_frequency(text_without_tz)
        day = self._extract_day(text_without_tz)

        # Build cron expression from components
        cron = self._build_cron(time, frequency, day)

        if not cron:
            return None

        confidence = self._calculate_confidence(text_without_tz, time, frequency, day)

        return ParsedSchedule(
            cron_expression=cron,
            description=self._generate_description(cron, timezone),
            confidence=confidence,
            timezone=timezone,
        )

    def _extract_time(self, text: str) -> tuple[int, int] | None:
        """Extract hour:minute from text.

        Handles formats like:
        - "8am", "8:30am", "8 AM", "8:30 AM"
        - "14:30" (24-hour)
        - "morning", "evening" (descriptors)
        """
        # Try explicit time with am/pm: "8am", "8:30am", "8 AM"
        match = re.search(r"(\d{1,2}):?(\d{2})?\s*(am|pm)", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2) or 0)
            period = match.group(3)

            # Validate ranges
            if hour < 1 or hour > 12 or minute > 59:
                return None

            # Convert to 24-hour format
            if period == "pm" and hour != 12:
                hour += 12
            elif period == "am" and hour == 12:
                hour = 0

            return (hour, minute)

        # Try 24-hour format: "14:30"
        match = re.search(r"(\d{1,2}):(\d{2})(?!\s*(am|pm))", text)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))

            # Validate 24-hour ranges
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return (hour, minute)

        # Try time descriptors: "morning", "evening"
        for descriptor, (hour, minute) in self.TIME_DESCRIPTORS.items():
            if descriptor in text:
                return (hour, minute)

        return None

    def _extract_frequency(self, text: str) -> str | None:
        """Extract frequency pattern.

        Handles patterns like:
        - "every 5 minutes", "every minute"
        - "every hour", "hourly"
        - "every day", "daily"
        - "every week", "weekly"
        - "every month", "monthly"
        """
        # Every N minutes
        match = re.search(r"every\s+(\d+)\s*minutes?", text)
        if match:
            n = match.group(1)
            return f"*/{n} * * * *"

        # Every minute (special case)
        if re.search(r"every\s+minute", text):
            return "* * * * *"

        # Every hour / hourly
        if re.search(r"(?:every\s+hour|hourly)", text):
            return "0 * * * *"

        # Every day / daily
        if re.search(r"(?:every\s+day|daily)", text):
            return "0 0 * * *"

        # Every week / weekly
        if re.search(r"(?:every\s+week|weekly)", text):
            return "0 0 * * 0"

        # Every month / monthly
        if re.search(r"(?:every\s+month|monthly)", text):
            return "0 0 1 * *"

        return None

    def _extract_day(self, text: str) -> int | str | None:
        """Extract day of week from text."""
        for day_name, day_num in self.DAY_PATTERNS.items():
            # Match as whole word with optional 's' suffix for plurals
            if re.search(rf"\b{day_name}s?\b", text):
                return day_num
        return None

    def _extract_timezone(self, text: str) -> str | None:
        """Extract timezone from text.

        Looks for patterns like:
        - "8am EST", "9pm PST"
        - "8am in New York", "9pm in Tokyo"
        """
        # Try explicit timezone abbreviations: "8am EST"
        match = re.search(r"\b([a-z]{3,4})\b", text)
        if match:
            tz_abbr = match.group(1).lower()
            if tz_abbr in self.TIMEZONE_ALIASES:
                return self.TIMEZONE_ALIASES[tz_abbr]

        # Try "in [city]" pattern: "8am in New York"
        # Match everything after "in " up to a time descriptor or end
        pattern = (
            r"\bin\s+([a-z\s]+?)"
            r"(?:\s+(?:at|on|every|daily|hourly|weekly|monthly)|\s*$)"
        )
        match = re.search(pattern, text)
        if match:
            city = match.group(1).strip().lower()
            if city in self.TIMEZONE_ALIASES:
                return self.TIMEZONE_ALIASES[city]

        return None

    def _remove_timezone(self, text: str, timezone: str | None) -> str:
        """Remove timezone indicators from text for cleaner parsing."""
        if not timezone:
            return text

        # Remove timezone abbreviation
        text = re.sub(r"\s+[a-z]{3,4}\b", "", text, count=1)

        # Remove "in [city]" pattern - match same pattern as extraction
        pattern = (
            r"\bin\s+[a-z\s]+?"
            r"(?:\s+(?:at|on|every|daily|hourly|weekly|monthly)|\s*$)"
        )
        text = re.sub(pattern, "", text, count=1)

        return text.strip()

    def _build_cron(
        self,
        time: tuple[int, int] | None,
        frequency: str | None,
        day: int | str | None,
    ) -> str | None:
        """Build cron expression from components."""
        # Case 1: Time + Day (no frequency) -> Weekly on that day
        if time and day is not None and not frequency:
            minute, hour = time[1], time[0]
            return f"{minute} {hour} * * {day}"

        # Case 2: Time only -> Daily at that time
        if time and not frequency and day is None:
            minute, hour = time[1], time[0]
            return f"{minute} {hour} * * *"

        # Case 3: Frequency only (with implied time) -> Use frequency's default
        if frequency and not time:
            return frequency

        # Case 4: Frequency + Time -> Override frequency's time
        if frequency and time:
            parts = frequency.split()
            parts[0] = str(time[1])  # minute
            parts[1] = str(time[0])  # hour

            # Add day if specified
            if day is not None and len(parts) >= 5:
                parts[4] = str(day)

            return " ".join(parts)

        # Case 5: Day only (no time, no frequency) -> Assume 9am
        if day is not None and not time and not frequency:
            return f"0 9 * * {day}"

        return None

    def _calculate_confidence(
        self,
        text: str,
        time: tuple | None,
        frequency: str | None,
        day: int | str | None,
    ) -> float:
        """Calculate parsing confidence.

        High confidence: clear time + clear frequency/day
        Medium confidence: time or frequency but not both clear
        Low confidence: ambiguous or vague input
        """
        score = 0.5  # Base confidence

        # Boost for explicit time
        if time:
            score += 0.2

        # Boost for explicit frequency or day
        if frequency:
            score += 0.15
        if day is not None:
            score += 0.15

        # Penalize vague words
        vague_words = ["sometimes", "occasionally", "maybe", "perhaps", "around"]
        if any(w in text for w in vague_words):
            score -= 0.3

        # Penalize very short input
        if len(text.split()) < 3:
            score -= 0.1

        return max(0.0, min(1.0, score))

    def _generate_description(self, cron: str, timezone: str | None) -> str:
        """Generate human-readable description of cron expression."""
        parts = cron.split()
        if len(parts) != 5:
            return f"Schedule: {cron}"

        minute, hour, dom, month, dow = parts

        # Handle special frequencies first (before trying to parse time)
        if minute.startswith("*/"):
            n = minute[2:]
            desc = f"Every {n} minutes"
            if timezone:
                tz_name = timezone.split("/")[-1].replace("_", " ")
                desc += f" ({tz_name} time)"
            return desc
        elif minute == "*":
            desc = "Every minute"
            if timezone:
                tz_name = timezone.split("/")[-1].replace("_", " ")
                desc += f" ({tz_name} time)"
            return desc

        # Build time description (only for non-wildcard hours)
        if hour != "*":
            hour_int = int(hour)
            minute_int = int(minute)

            # Format time in 12-hour format with am/pm
            if hour_int == 0:
                time_str = f"12:{minute_int:02d} AM"
            elif hour_int < 12:
                time_str = f"{hour_int}:{minute_int:02d} AM"
            elif hour_int == 12:
                time_str = f"12:{minute_int:02d} PM"
            else:
                time_str = f"{hour_int - 12}:{minute_int:02d} PM"
        else:
            time_str = None

        # Build frequency description
        if dow == "*" and dom == "*":
            freq_str = "daily"
        elif dow == "1-5":
            freq_str = "on weekdays"
        elif dow == "0,6":
            freq_str = "on weekends"
        elif dow != "*":
            day_names = {
                "0": "Sundays",
                "1": "Mondays",
                "2": "Tuesdays",
                "3": "Wednesdays",
                "4": "Thursdays",
                "5": "Fridays",
                "6": "Saturdays",
            }
            freq_str = f"on {day_names.get(dow, dow)}"
        else:
            freq_str = ""

        # Handle remaining cases
        if hour == "*" and freq_str:
            desc = f"Every hour {freq_str}"
        elif dom == "1" and month == "*" and time_str:
            desc = f"Monthly at {time_str}"
        elif time_str:
            desc = f"At {time_str} {freq_str}".strip()
        else:
            desc = f"Schedule: {cron}"

        # Add timezone if specified
        if timezone:
            tz_name = timezone.split("/")[-1].replace("_", " ")
            desc += f" ({tz_name} time)"

        return desc

    def clarify(self, text: str) -> str:
        """Generate a clarification question for low-confidence input.

        Args:
            text: The original natural language input

        Returns:
            A question asking for clarification
        """
        text_lower = text.lower()

        # Check what's missing
        has_time = self._extract_time(text_lower) is not None
        has_frequency = self._extract_frequency(text_lower) is not None
        has_day = self._extract_day(text_lower) is not None

        if not has_time and not has_frequency:
            return (
                "I'm not sure when you want this to run. "
                "Could you be more specific? For example:\n"
                "- 'every morning at 8am'\n"
                "- 'every 30 minutes'\n"
                "- 'Sundays at 7pm'"
            )

        if not has_time and has_frequency:
            return (
                f"You said '{text}' but I need to know what time. "
                "What time should this run?"
            )

        if has_time and not has_frequency and not has_day:
            return (
                "You want this at a specific time, but how often? "
                "Every day, or just certain days?"
            )

        return (
            "I'm not quite sure I understand. "
            "Could you rephrase that? Try something like:\n"
            "- 'every morning at 8am'\n"
            "- 'weekdays at 9am'\n"
            "- 'every 15 minutes'"
        )
