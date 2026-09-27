SYSTEM_PLANNER = """You are an expert travel itinerary planner.

HARD RULES
- Use ONLY places from CANDIDATES, referenced by their `ref`. Never invent places.
- Never use the same place twice in the whole trip.
- Output exactly the requested number of days, numbered from 1.
- Stops per day: relaxed 2-4, balanced 3-5, packed 5-7 (meals count as stops).
- Days run between 08:30 and 21:30. Leave realistic travel time between stops (~15 min if close together, more if far).
- Every stop must fall inside that place's opening hours for that day (hours shown per weekday).
- Include a lunch and a dinner stop each day, chosen from `food` candidates.
- Group geographically close places on the same day; avoid zig-zagging across the city.
- Respect the budget level. Avoid places whose price level is far above it.

QUALITY
- Prioritize the traveler's interests, but keep some variety.
- `rationale`: one short sentence tying the stop to the traveler's interests.

Call the `submit` tool with the itinerary."""

def compact_hours(c, gday: int) -> str:
    if not c.open_periods:
        return "?"
    spans = [f"{p.open_h:02d}:{p.open_m:02d}-{p.close_h:02d}:{p.close_m:02d}"
             for p in c.open_periods if p.open_day == gday]
    return ",".join(spans) or "closed"

def render_candidates(cands, weekdays) -> str:
    lines = []
    for c in cands:
        hrs = " | ".join(f"{name}:{compact_hours(c, g)}" for g, name in weekdays)
        price = "?" if c.price_level is None else "$" * max(c.price_level, 1)
        lines.append(f"{c.ref} | {c.name} | {c.category} | {c.rating or '?'}star({c.rating_count or 0}) "
                     f"| {price} | {c.lat:.4f},{c.lng:.4f} | ~{c.typical_duration_min}min | {hrs}")
    return "\n".join(lines)

def repair_prompt(hard_violations) -> str:
    lines = "\n".join(f"- [{x.code}] {x.message}" for x in hard_violations)
    return ("Your itinerary has these problems:\n" + lines +
            "\nFix ONLY what is needed, keep the rest unchanged, use only refs from CANDIDATES, "
            "and call submit with the full corrected itinerary.")