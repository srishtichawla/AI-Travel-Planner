from datetime import date

from app import tracking
from app.config import settings
from app.schemas import TripRequest


def test_finish_run_splits_llm_and_maps_cost(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "db_path", str(tmp_path / "t.db"))
    tracking.init_db()
    req = TripRequest(destination="Lisbon", days=1, start_date=date(2026, 11, 9))
    rid = tracking.start_run(req, tag="test")
    tracking.log_llm(name="plan", model="claude-sonnet-5", input_tokens=1000, output_tokens=500,
                     cache_read=0, cache_write=0, latency_ms=10, ok=True)
    with tracking.track_maps("places_text_search"):
        pass
    tracking.log_cache_hit("maps", "places_text_search")
    m = tracking.finish_run(rid, ok=True, total_ms=50, repair_rounds=0, first_pass_hard=0)

    assert abs(m.llm_cost_usd - tracking.llm_cost("claude-sonnet-5", 1000, 500)) < 1e-9
    assert abs(m.maps_cost_usd - tracking.MAPS_PRICES["places_text_search"]) < 1e-9
    assert abs(m.cost_usd - (m.llm_cost_usd + m.maps_cost_usd)) < 1e-9
    assert m.maps_calls == 1
    assert m.cache_hits == 1
