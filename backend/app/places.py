import contextvars
import hashlib
import math
from concurrent.futures import ThreadPoolExecutor

import httpx

from . import cache, tracking
from .config import settings
from .schemas import Candidate, OpenPeriod, TripRequest

URL = "https://places.googleapis.com/v1/places:searchText"
FIELDS = ",".join(f"places.{f}" for f in [
    "id", "displayName", "location", "rating", "userRatingCount", "priceLevel",
    "types", "primaryType", "regularOpeningHours", "formattedAddress"])
PRICE = {"PRICE_LEVEL_FREE": 0, "PRICE_LEVEL_INEXPENSIVE": 1, "PRICE_LEVEL_MODERATE": 2,
         "PRICE_LEVEL_EXPENSIVE": 3, "PRICE_LEVEL_VERY_EXPENSIVE": 4}
TTL_S = 3 * 24 * 3600
DURATION = {"food": 75, "attraction": 90, "nature": 120, "nightlife": 120, "shopping": 60, "other": 60}

_client = httpx.Client(timeout=15)


def text_search(query: str, page_size: int = 15) -> list[dict]:
    key = "places:" + hashlib.sha1(f"{query}|{page_size}".encode()).hexdigest()
    if (hit := cache.get(key)) is not None:
        tracking.log_cache_hit("maps", "places_text_search")
        return hit
    with tracking.track_maps("places_text_search"):
        r = _client.post(URL,
                         json={"textQuery": query, "pageSize": page_size, "languageCode": "en"},
                         headers={"X-Goog-Api-Key": settings.google_maps_api_key,
                                  "X-Goog-FieldMask": FIELDS})
        r.raise_for_status()
    places = r.json().get("places", [])
    cache.set(key, places, TTL_S)
    return places


def _category(types: list[str], query_kind: str) -> str:
    t = set(types)
    if query_kind == "food" or t & {"restaurant", "cafe", "bakery", "bar"}:
        return "food"
    if t & {"night_club", "bar"}:
        return "nightlife"
    if t & {"park", "natural_feature", "hiking_area", "beach"}:
        return "nature"
    if t & {"shopping_mall", "store", "market"}:
        return "shopping"
    if t & {"tourist_attraction", "museum", "church", "art_gallery", "historical_landmark"}:
        return "attraction"
    return "other"


def _periods(p: dict) -> list[OpenPeriod]:
    out = []
    for per in (p.get("regularOpeningHours") or {}).get("periods", []):
        o, c = per.get("open"), per.get("close")
        if not o or not c:
            return []
        out.append(OpenPeriod(open_day=o["day"], open_h=o.get("hour", 0), open_m=o.get("minute", 0),
                              close_day=c["day"], close_h=c.get("hour", 0), close_m=c.get("minute", 0)))
    return out


def _to_candidate(p: dict, kind: str, source: str) -> Candidate:
    cat = _category(p.get("types", []), kind)
    return Candidate(
        ref="", place_id=p["id"], name=p["displayName"]["text"], category=cat,
        lat=p["location"]["latitude"], lng=p["location"]["longitude"],
        address=p.get("formattedAddress", ""), rating=p.get("rating"),
        rating_count=p.get("userRatingCount"), price_level=PRICE.get(p.get("priceLevel")),
        open_periods=_periods(p), sources=[source], typical_duration_min=DURATION[cat])


def compact_hours(c: Candidate, gday: int) -> str:
    if not c.open_periods:
        return "?"
    spans = [f"{p.open_h:02d}:{p.open_m:02d}-{p.close_h:02d}:{p.close_m:02d}"
             for p in c.open_periods if p.open_day == gday]
    return ",".join(spans) or "closed"


def gather_candidates(req: TripRequest, max_candidates: int = 45) -> list[Candidate]:
    d = req.destination
    queries = [(f"top attractions in {d}", "attraction", "general"),
               (f"best restaurants in {d}", "food", "food")]
    if req.budget_level == "budget":
        queries.append((f"cheap eats in {d}", "food", "food"))
    if req.budget_level == "luxury":
        queries.append((f"fine dining in {d}", "food", "food"))
    queries += [(f"{i} in {d}", "other", i) for i in req.interests]

    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda q: ctx.copy().run(text_search, q[0]), queries))

    merged: dict[str, Candidate] = {}
    for (q, kind, source), places in zip(queries, results):
        for p in places:
            c = _to_candidate(p, kind, source)
            if c.place_id in merged:
                merged[c.place_id].sources = sorted(set(merged[c.place_id].sources) | {source})
            else:
                merged[c.place_id] = c

    good = [c for c in merged.values() if (c.rating or 0) >= 4.0 and (c.rating_count or 0) >= 50]
    good.sort(key=lambda c: (c.rating or 0) * math.log10((c.rating_count or 1) + 1), reverse=True)
    picked = good[:max_candidates]
    for i, c in enumerate(picked, 1):
        c.ref = f"c{i}"
    return picked