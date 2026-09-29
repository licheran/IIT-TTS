"""Slot arithmetic and allowed start times (spec 02 section 4).

A slot is `t = day_index * P + period_index`, where `P` is the number of periods per day and the
indexes follow the `order` of days and periods. An event starting at `t` covers
`t ... t + duration - 1`.
"""

from tts.core.model import Event, StartPattern, TimeModel


class TimeGridError(ValueError):
    """A code or slot that the time model does not contain."""


def covered_slots(start: int, duration: int) -> range:
    """The slots an event of `duration` covers when it starts at `start`."""
    return range(start, start + duration)


class TimeGrid:
    """Index over a `TimeModel`. Build once, query many times."""

    def __init__(self, time_model: TimeModel) -> None:
        self._days = tuple(d.code for d in time_model.days)
        self._periods = tuple(p.code for p in time_model.periods)
        self._day_index = {code: i for i, code in enumerate(self._days)}
        self._period_index = {code: i for i, code in enumerate(self._periods)}
        self._breaks = tuple(p.is_break for p in time_model.periods)
        self._patterns = {s.code: s for s in time_model.start_patterns}

    @property
    def periods_per_day(self) -> int:
        return len(self._periods)

    @property
    def day_count(self) -> int:
        return len(self._days)

    @property
    def slot_count(self) -> int:
        return self.day_count * self.periods_per_day

    def slot(self, day: str, period: str) -> int:
        """The slot index of a day code and a period code."""
        return self._day(day) * self.periods_per_day + self._period(period)

    def day_index(self, t: int) -> int:
        return t // self.periods_per_day

    def period_index(self, t: int) -> int:
        return t % self.periods_per_day

    def codes(self, t: int) -> tuple[str, str]:
        """The (day code, period code) of a slot."""
        if not 0 <= t < self.slot_count:
            raise TimeGridError(f"slot {t} is outside the grid of {self.slot_count} slots")
        return self._days[self.day_index(t)], self._periods[self.period_index(t)]

    def is_break(self, t: int) -> bool:
        return self._breaks[self.period_index(t)]

    def allowed_starts(self, event: Event) -> tuple[int, ...]:
        """Ascending slots where `event` may start.

        The day must be allowed by the pattern, the period must be one of its start periods, and
        the whole span must lie in one day without covering a break.
        """
        pattern = self._pattern(event.start_pattern)
        per_day = self.periods_per_day
        days = self._pattern_days(pattern)
        periods = sorted({self._period(code) for code in pattern.start_periods})
        starts = []
        for day in days:
            for period in periods:
                end = period + event.duration
                if end > per_day:
                    continue
                if any(self._breaks[p] for p in range(period, end)):
                    continue
                starts.append(day * per_day + period)
        return tuple(starts)

    def _pattern_days(self, pattern: StartPattern) -> list[int]:
        if pattern.days is None:
            return list(range(self.day_count))
        return sorted({self._day(code) for code in pattern.days})

    def _pattern(self, code: str) -> StartPattern:
        try:
            return self._patterns[code]
        except KeyError:
            raise TimeGridError(f'unknown start pattern "{code}"') from None

    def _day(self, code: str) -> int:
        try:
            return self._day_index[code]
        except KeyError:
            raise TimeGridError(f'unknown day "{code}"') from None

    def _period(self, code: str) -> int:
        try:
            return self._period_index[code]
        except KeyError:
            raise TimeGridError(f'unknown period "{code}"') from None


def allowed_starts(event: Event, time_model: TimeModel) -> tuple[int, ...]:
    """Convenience wrapper. Build a `TimeGrid` once when calling this for many events."""
    return TimeGrid(time_model).allowed_starts(event)
