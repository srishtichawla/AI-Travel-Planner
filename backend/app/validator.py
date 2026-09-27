from datetime import timedelta

from . import routes
from .schemas import Candidate, PlannedItinerary, TripRequest, Violation

PACE_LIMITS = {"relaxed": (2, 4), "balanced": (3, 5), "packed": (5, 7)}
BUDGET_MAX_AVG_PRICE = {"budget": 1.5, "moderate": 2.5, "luxury": 4.0}
DAY_START, DAY_END = 8 * 60 + 30, 21 * 60 + 30


def hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def is_open(c: Candidate, gday: int, start: int, end: int) -> bool:
    if not c.open_periods:
        return True
    for p in c.open_periods:
        if p.open_day != gday:
            continue
        o = p.open_h * 60 + p.open_m
        cl = p.close_h * 60 + p.close_m + (0 if p.close_day == p.open_day else 24 * 60)
        if o <= start and end <= cl:
            return True
    return False


def validate(req: TripRequest, by_ref: dict[str, Candidate], plan: PlannedItinerary) -> list[Violation]:
    v: list[Violation] = []

    def hard(code, msg, **k):
        v.append(Violation(code=code, severity="hard", message=msg, **k))

    def soft(code, msg, **k):
        v.append(Violation(code=code, severity="soft", message=msg, **k))

    if [d.day for d in plan.days] != list(range(1, req.days + 1)):
        hard("day_count", f"Expected days 1..{req.days}, got {[d.day for d in plan.days]}")

    seen: set[str] = set()
    prices: list[int] = []
    lo, hi = PACE_LIMITS[req.pace]

    for d in plan.days:
        date_ = req.start_date + timedelta(days=d.day - 1)
        gday = (date_.weekday() + 1) % 7
        if not lo <= len(d.stops) <= hi:
            hard("pace", f"Day {d.day} has {len(d.stops)} stops; {req.pace} pace needs {lo}-{hi}", day=d.day)
        if not any(by_ref.get(s.ref) and by_ref[s.ref].category == "food" for s in d.stops):
            soft("no_meal", f"Day {d.day} has no food stop", day=d.day)

        ordered = sorted(d.stops, key=lambda s: hm(s.start_time))
        resolved = []
        for s in ordered:
            c = by_ref.get(s.ref)
            if c is None:
                hard("unknown_ref", f"'{s.ref}' is not in CANDIDATES", day=d.day, ref=s.ref)
                continue
            if s.ref in seen:
                hard("duplicate", f"{c.name} ({s.ref}) used more than once", day=d.day, ref=s.ref)
            seen.add(s.ref)
            start, end = hm(s.start_time), hm(s.start_time) + s.duration_min
            if start < DAY_START or end > DAY_END:
                hard("day_bounds", f"{c.name} runs {s.start_time}+{s.duration_min}min, outside 08:30-21:30",
                     day=d.day, ref=s.ref)
            if not is_open(c, gday, start, end):
                hard("closed", f"{c.name} is closed {s.start_time}-{end // 60:02d}:{end % 60:02d} on day {d.day}",
                     day=d.day, ref=s.ref)
            if c.price_level is not None:
                prices.append(c.price_level)
            resolved.append((s, c, start, end))

        legs = routes.legs_for_day([c for _, c, _, _ in resolved]) if len(resolved) > 1 else []
        for i, (s, c, start, end) in enumerate(resolved[1:], 1):
            need = legs[i - 1].minutes
            gap = start - resolved[i - 1][3]
            if gap < need:
                hard("travel", f"Only {gap} min between {resolved[i - 1][1].name} and {c.name}; travel takes {need} min",
                     day=d.day, ref=s.ref)

    if prices and sum(prices) / len(prices) > BUDGET_MAX_AVG_PRICE[req.budget_level]:
        soft("budget", f"Average price level {sum(prices) / len(prices):.1f} too high for {req.budget_level}")
    return v