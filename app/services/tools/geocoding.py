from typing import Any, Dict, List, Optional, Sequence, Tuple
import os
import json
import requests
from cachetools import TTLCache, cached
from requests.adapters import HTTPAdapter, Retry

cache = TTLCache(maxsize=1024, ttl=86400)

COUNTRY_BIAS: str = os.getenv("DELIVERY_COUNTRY_BIAS", "UA")
LANGUAGE: str = os.getenv("DELIVERY_LANGUAGE", "uk")
GOOGLE_MAPS_API_KEY: Optional[str] = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyD7MfLNeZ8TvhFpfWgFouJpA2ATtNsGewQ")
USER_AGENT: str = os.getenv("DELIVERY_HTTP_UA", "BoxCatering-DeliveryBot/1.0")
HTTP_TIMEOUT_S: float = float(os.getenv("DELIVERY_HTTP_TIMEOUT", "10"))
HTTP_RETRIES: int = int(os.getenv("DELIVERY_HTTP_RETRIES", "3"))
HTTP_BACKOFF: float = float(os.getenv("DELIVERY_HTTP_BACKOFF", "0.4"))
NOMINATIM_EMAIL: Optional[str] = os.getenv("NOMINATIM_EMAIL")

def make_session() -> requests.Session:
    s = requests.Session()
    retries = Retry(
        total=HTTP_RETRIES,
        backoff_factor=HTTP_BACKOFF,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "POST"]),
    )
    s.headers.update({"User-Agent": USER_AGENT})
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s


def is_finite(x: Any) -> bool:
    try:
        from math import isfinite
        return isfinite(float(x))
    except Exception:
        return False

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


@cached(cache)
def get_delivery_zones() -> List[Dict[str, Any]]:
    data: List[Dict[str, Any]] = []
    for i in range(1, 3):
        r = make_session().get(f"https://back.box-catering.ua/api/cities/{i}/delivery-zones", timeout=HTTP_TIMEOUT_S)
        r.raise_for_status()
        zones = r.json()
        require(isinstance(zones, list) and zones, "Empty delivery zones response.")
        data.extend(zones)
    return data


def geocode_google(query: str) -> Optional[Dict[str, Any]]:
    require(GOOGLE_MAPS_API_KEY, "GOOGLE_MAPS_API_KEY is not set.")
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": query, "key": GOOGLE_MAPS_API_KEY, "language": LANGUAGE, "components": f"country:{COUNTRY_BIAS}"}
    r = make_session().get(url, params=params, timeout=HTTP_TIMEOUT_S)
    r.raise_for_status()
    payload = r.json()

    if payload.get("status") != "OK":
        return None

    results = payload.get("results") or []
    if not results:
        return None

    best = results[0]
    loc = (best.get("geometry") or {}).get("location") or {}

    lat, lng = loc.get("lat"), loc.get("lng")
    if not (is_finite(lat) and is_finite(lng)):
        return None

    components: Dict[str, str] = {}
    for comp in best.get("address_components", []):
        for tpe in comp.get("types", []):
            if tpe not in components:
                components[tpe] = comp.get("long_name")

    types = best.get("types", []) or []
    conf = (
        0.95 if "street_address" in types else
        0.90 if ("premise" in types or "subpremise" in types) else
        0.80 if "route" in types else
        0.60 if "locality" in types else
        0.50
    )

    return {
        "lat": float(lat),
        "lng": float(lng),
        "formatted": best.get("formatted_address"),
        "place_id": best.get("place_id"),
        "provider": "google",
        "components": components,
        "confidence": conf,
    }


def geocode_nominatim(query: str) -> Optional[Dict[str, Any]]:
    url = "https://nominatim.openstreetmap.org/search"
    headers = {"Accept-Language": LANGUAGE}
    if NOMINATIM_EMAIL:
        headers["From"] = NOMINATIM_EMAIL

    params = {"q": query, "format": "json", "addressdetails": 1, "limit": 1, "countrycodes": COUNTRY_BIAS.lower()}
    r = make_session().get(url, params=params, headers=headers, timeout=HTTP_TIMEOUT_S + 2)
    r.raise_for_status()
    data = r.json()

    if not data:
        return None

    best = data[0]
    lat, lon = best.get("lat"), best.get("lon")

    if not (is_finite(lat) and is_finite(lon)):
        return None

    cls = f"{best.get('class') or ''}:{best.get('type') or ''}"
    conf = (
        0.90 if ("building" in cls or "house" in cls) else
        0.80 if "highway" in cls else
        0.60 if any(x in cls for x in ("city", "town", "village")) else
        0.50
    )

    return {
        "lat": float(lat),
        "lng": float(lon),
        "formatted": best.get("display_name"),
        "place_id": str(best.get("osm_id") or ""),
        "provider": "nominatim",
        "components": best.get("address", {}) or {},
        "confidence": conf,
    }


def geocode(query: str, providers: Sequence[str] = ("google", "nominatim")) -> Dict[str, Any]:
    require(isinstance(query, str) and query.strip(), "Empty address query.")
    last_err: Optional[Exception] = None

    for p in providers:
        try:
            res = geocode_google(query) if p == "google" else geocode_nominatim(query) if p == "nominatim" else None
            if res:
                return res
        except Exception as e:
            last_err = e
            continue

    raise ValueError(f"Failed to geocode address: {last_err or 'Unknown error'}")


def point_on_segment(p: Dict[str, float], a: Dict[str, float], b: Dict[str, float], eps: float = 1e-9) -> bool:
    cross = (p["lat"] - a["lat"]) * (b["lng"] - a["lng"]) - (p["lng"] - a["lng"]) * (b["lat"] - a["lat"])
    if abs(cross) > eps:
        return False
    mnx, mxx = (a["lng"], b["lng"]) if a["lng"] <= b["lng"] else (b["lng"], a["lng"])
    mny, mxy = (a["lat"], b["lat"]) if a["lat"] <= b["lat"] else (b["lat"], a["lat"])
    return (mnx - eps) <= p["lng"] <= (mxx + eps) and (mny - eps) <= p["lat"] <= (mxy + eps)


def bbox_of_polygon(poly: List[Dict[str, float]]) -> Tuple[float, float, float, float]:
    lats = [pt["lat"] for pt in poly]
    lngs = [pt["lng"] for pt in poly]
    return min(lats), min(lngs), max(lats), max(lngs)


def point_in_polygon(point: Dict[str, float], polygon: List[Dict[str, float]]) -> bool:
    n = len(polygon)

    for i in range(n):
        if point_on_segment(point, polygon[i - 1], polygon[i]):
            return True

    x, y = point["lng"], point["lat"]
    inside = False
    j = n - 1

    for i in range(n):
        xi, yi = polygon[i]["lng"], polygon[i]["lat"]
        xj, yj = polygon[j]["lng"], polygon[j]["lat"]

        if (yi > y) != (yj > y):
            x_int = (xj - xi) * (y - yi) / ((yj - yi) or 1e-16) + xi
            if x < x_int:
                inside = not inside
        j = i

    return inside


def get_delivery_by_point(
    zones: List[Dict[str, Any]],
    point: Dict[str, float],
    subtotal: Optional[float] = None,
) -> Dict[str, Any]:

    require(isinstance(zones, list) and zones, "Delivery zones list is empty.")
    require(point is not None and is_finite(point.get("lat")) and is_finite(point.get("lng")), "Invalid coordinates.")

    hits: List[Tuple[Dict[str, Any], Any]] = []

    for zone in zones:
        for poly in zone.get("polygons") or []:
            coords: List[Dict[str, float]] = poly.get("coords") or []
            if len(coords) < 3:
                continue

            min_lat, min_lng, max_lat, max_lng = bbox_of_polygon(coords)
            lat, lng = point["lat"], point["lng"]

            if not (min_lat - 1e-9 <= lat <= max_lat + 1e-9 and min_lng - 1e-9 <= lng <= max_lng + 1e-9):
                continue

            if point_in_polygon(point, coords):
                hits.append((zone, poly.get("id")))

    if not hits:
        return {"error": "Delivery is not available in this location."}

    for key in ("delivery_cost", "free_delivery"):
        for hit, _ in hits:
            value = hit.get(key)
            if value is None:
                hit[key] = 0.0
            else:
                try:
                    hit[key] = float(value)
                except (TypeError, ValueError):
                    hit[key] = 0.0

    hits.sort(key=lambda z: z[0]["delivery_cost"])
    chosen, polygon_id = hits[0]

    base_price = float(chosen.get("delivery_cost", 0))
    no_free = int(chosen.get("no_free_shipping", 0)) == 1
    free_threshold = float(chosen.get("free_delivery", float("inf")))

    is_free = False
    if not no_free and subtotal is not None and is_finite(subtotal):
        if subtotal >= free_threshold and chosen.get("title") == "Безкоштовна доставка":
            is_free = True

    price = 0.0 if is_free else base_price

    return {"price": price}


def get_delivery_price(
    query: str,
    subtotal: Optional[float] = None,
    providers: Sequence[str] = ("google", "nominatim"),
) -> Dict[str, Any]:
    min_confidence: float = 0.55

    geo = geocode(query, providers=providers)

    require(is_finite(geo.get("lat")) and is_finite(geo.get("lng")), "Failed to read coordinates.")

    point = {"lat": float(geo["lat"]), "lng": float(geo["lng"])}
    zones_data = get_delivery_zones()

    delivery = get_delivery_by_point(zones_data, point, subtotal=subtotal)

    return {
        "address": {
            "query": query,
            "formatted": geo.get("formatted"),
            "confidence": geo.get("confidence"),
        },
        "delivery": delivery,
    }


if __name__ == "__main__":
    try:
        result = get_delivery_price(
            query="Київ, Соборна 72",
            subtotal=30100,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {e}")
