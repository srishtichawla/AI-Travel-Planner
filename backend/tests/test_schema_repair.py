import json

from app.schemas import PlannedItinerary

STOP = {"ref": "c1", "start_time": "09:00", "duration_min": 60, "rationale": "x"}
GOOD = {"days": [{"day": 1, "stops": [STOP]}]}


def test_wrapped_key_is_unwrapped():
    p = PlannedItinerary.model_validate({"parameter name": GOOD})
    assert len(p.days) == 1


def test_stringified_days_with_trailing_text():
    s = json.dumps(GOOD["days"]) + " some trailing words"
    p = PlannedItinerary.model_validate({"days": s})
    assert p.days[0].stops[0].ref == "c1"


def test_empty_start_time_stop_is_dropped():
    bad_stop = {**STOP, "ref": "c2", "start_time": ""}
    p = PlannedItinerary.model_validate({"days": [{"day": 1, "stops": [STOP, bad_stop]}]})
    assert [s.ref for s in p.days[0].stops] == ["c1"]


def test_single_digit_hour_is_normalized():
    odd = {**STOP, "start_time": "9:30"}
    p = PlannedItinerary.model_validate({"days": [{"day": 1, "stops": [odd]}]})
    assert p.days[0].stops[0].start_time == "09:30"


def test_clean_input_is_unchanged():
    p = PlannedItinerary.model_validate(GOOD)
    assert p.days[0].stops[0].start_time == "09:00"
