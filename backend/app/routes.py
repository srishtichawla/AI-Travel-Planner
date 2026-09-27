import contextvars
import itertools
import math
from concurrent.futures import ThreadPoolExecutor

import httpx

from . import cache, tracking
from .config import settings
from .schemas import Candidate, Leg

URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


def haversine_m(a: Candidate, b: Candidate) -> float:
    R = 6371000
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi, dl = p2 - p1, math.radians(b.lng - a.lng)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _fallback(a: Candidate, b: Candidate, mode: str) -> Leg:
    m = haversine_m(a, b) * 1.3
    speed = 4500 if mode == "WALK" else 25000
    return Leg(minutes=round(m / speed * 60), meters=int(m), mode=mode, estimated=True)


def leg(a: Candidate, b: Candidate) -> Leg:
    mode = "WALK" if haversine_m(a, b) < 1500 else "DRIVE"
    key = f"route:{a.place_id}:{b.place_id}:{mode}"
    if (hit := cache.get(key)) is not None:
        tracking.log_cache_hit("maps", "routes_compute")
        return Leg(**hit)
    body = {"origin": {"placeId": a.place_id}, "destination": {"placeId": b.place_id}, "travelMode": mode}
    if mode == "DRIVE":
        body["routingPreference"] = "TRAFFIC_UNAWARE"
    try:
        with tracking.track_maps("routes_compute"):
            r = httpx.post(URL, json=body, timeout=15, headers={
                "X-Goog-Api-Key": settings.google_maps_api_key,
                "X-Goog-FieldMask": "routes.duration,routes.distanceMeters"})
            r.raise_for_status()
        route = r.json()["routes"][0]
        result = Leg(minutes=round(int(route["duration"].rstrip("s")) / 60),
                     meters=route.get("distanceMeters", 0), mode=mode)
    except Exception:  # noqa: BLE001 - any failure here should fall back to an estimate, not crash
        return _fallback(a, b, mode)
    cache.set(key, result.model_dump(), 7 * 24 * 3600)
    return result


def legs_for_day(stops: list[Candidate]) -> list[Leg]:
    ctx = contextvars.copy_context()
    pairs = list(itertools.pairwise(stops))
    with ThreadPoolExecutor(max_workers=6) as pool:
        return list(pool.map(lambda p: ctx.copy().run(leg, *p), pairs))