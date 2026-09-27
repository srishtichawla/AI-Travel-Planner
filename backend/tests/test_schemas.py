from datetime import date

from app.fixtures import lisbon_candidates
from app.schemas import PlannedStop, TripRequest


def test_trip_request_defaults():
    r = TripRequest(destination="Lisbon", days=2, start_date=date(2026, 11, 2))
    assert r.budget_level == "moderate"
    assert r.pace == "balanced"
    assert r.interests == []

def test_trip_request_rejects_too_many_days():
    import pytest
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        TripRequest(destination="Lisbon", days=10, start_date=date(2026, 11, 2))

def test_fixtures_load():
    cands = lisbon_candidates()
    assert len(cands) == 13
    refs = [c.ref for c in cands]
    assert len(refs) == len(set(refs))          # all unique
    assert all(c.place_id.startswith("FIX_") for c in cands)

def test_planned_stop_time_pattern():
    import pytest
    from pydantic import ValidationError
    PlannedStop(ref="c1", start_time="09:00", duration_min=60, rationale="test")
    with pytest.raises(ValidationError):
        PlannedStop(ref="c1", start_time="9:00", duration_min=60, rationale="test")  # missing leading zero
        