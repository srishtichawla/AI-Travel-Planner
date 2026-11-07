from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class TripRequest(BaseModel):
    destination: str = Field(min_length=2, max_length=80)
    days: int = Field(ge=1, le=7)
    start_date: date
    budget_level: Literal["budget", "moderate", "luxury"] = "moderate"
    interests: list[str] = Field(default_factory=list, max_length=6)
    pace: Literal["relaxed", "balanced", "packed"] = "balanced"


class OpenPeriod(BaseModel):
    open_day: int
    open_h: int
    open_m: int
    close_day: int
    close_h: int
    close_m: int


class Candidate(BaseModel):
    ref: str
    place_id: str
    name: str
    category: Literal["food", "attraction", "nature", "nightlife", "shopping", "other"]
    lat: float
    lng: float
    address: str = ""
    rating: float | None = None
    rating_count: int | None = None
    price_level: int | None = None
    open_periods: list[OpenPeriod] = []
    sources: list[str] = []
    typical_duration_min: int = 60


class PlannedStop(BaseModel):
    ref: str = Field(description="Candidate ref such as c12. MUST exist in CANDIDATES.")
    start_time: str = Field(description="24h HH:MM", pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    duration_min: int = Field(ge=1, le=300)
    rationale: str = Field(max_length=200, description="Why this stop fits the traveler")

    @field_validator("duration_min", mode="before")
    @classmethod
    def _clamp_min_duration(cls, v):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return v
        return max(v, 15)


class PlannedDay(BaseModel):
    day: int = Field(ge=1, le=7)
    stops: list[PlannedStop]


def _first_json(text):
    import json

    obj, _ = json.JSONDecoder().raw_decode(text.strip())
    return obj


def _norm_time(t):
    import re

    if not isinstance(t, str):
        return None
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", t)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if h > 23 or mi > 59:
        return None
    return f"{h:02d}:{mi:02d}"


class PlannedItinerary(BaseModel):
    days: list[PlannedDay]

    @model_validator(mode="before")
    @classmethod
    def _repair_shape(cls, data):
        if isinstance(data, str):
            data = _first_json(data)
        while isinstance(data, dict) and "days" not in data and len(data) == 1:
            data = next(iter(data.values()))
            if isinstance(data, str):
                data = _first_json(data)
        if isinstance(data, list):
            data = {"days": data}
        if not isinstance(data, dict):
            return data
        days = data.get("days")
        if isinstance(days, str):
            days = _first_json(days)
        if isinstance(days, list):
            fixed = []
            for d in days:
                if isinstance(d, dict) and isinstance(d.get("stops"), list):
                    stops = []
                    for st in d["stops"]:
                        if not isinstance(st, dict):
                            continue
                        t = _norm_time(st.get("start_time"))
                        if t is None:
                            continue
                        stops.append({**st, "start_time": t})
                    d = {**d, "stops": stops}
                fixed.append(d)
            data = {**data, "days": fixed}
        return data


class Violation(BaseModel):
    code: str
    severity: Literal["hard", "soft"]
    day: int | None = None
    ref: str | None = None
    message: str


class Leg(BaseModel):
    minutes: int
    meters: int
    mode: Literal["WALK", "DRIVE"]
    estimated: bool = False


class EnrichedStop(PlannedStop):
    place_id: str
    name: str
    category: str
    lat: float
    lng: float
    address: str
    rating: float | None
    price_level: int | None
    leg_from_prev: Leg | None = None


class EnrichedDay(BaseModel):
    day: int
    date: date
    stops: list[EnrichedStop]


class RunMetrics(BaseModel):
    run_id: str
    cost_usd: float
    latency_ms: float
    llm_calls: int
    maps_calls: int
    cache_hits: int
    repair_rounds: int
    first_pass_hard_violations: int


class PlanResponse(BaseModel):
    days: list[EnrichedDay]
    violations: list[Violation]
    metrics: RunMetrics
