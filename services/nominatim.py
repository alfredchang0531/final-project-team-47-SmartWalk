import os
import time
import math
from typing import Any, Dict, List, Optional, Tuple

import requests


class NominatimError(Exception):
    """Raised when Nominatim requests fail."""


NOMINATIM_BASE_URL = os.getenv("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org")
NOMINATIM_USER_AGENT = os.getenv(
    "NOMINATIM_USER_AGENT", "WalkSmart/1.0 (https://github.com/alfredchang0531/final-project-team-47-SmartWalk)"
)
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))
CACHE_TTL_SECONDS = int(os.getenv("NOMINATIM_CACHE_TTL", "300"))
MIN_REQUEST_INTERVAL_SECONDS = float(os.getenv("NOMINATIM_MIN_INTERVAL", "1.0"))

_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Tuple[float, Any]] = {}
_LAST_REQUEST_AT = 0.0

CATEGORY_TAGS = {
    "cafe": {"amenity": "cafe"},
    "restaurant": {"amenity": "restaurant"},
    "pharmacy": {"amenity": "pharmacy"},
    "convenience_store": {"amenity": "convenience"},
    "park": {"leisure": "park"},
}


def _throttle() -> None:
    global _LAST_REQUEST_AT
    elapsed = time.monotonic() - _LAST_REQUEST_AT
    wait_time = MIN_REQUEST_INTERVAL_SECONDS - elapsed
    if wait_time > 0:
        time.sleep(wait_time)
    _LAST_REQUEST_AT = time.monotonic()


def _request(endpoint: str, params: Dict[str, Any]) -> Any:
    key = (endpoint, tuple(sorted((str(k), str(v)) for k, v in params.items())))
    now = time.time()
    cached = _CACHE.get(key)
    if cached and cached[0] > now:
        return cached[1]

    _throttle()

    try:
        response = requests.get(
            f"{NOMINATIM_BASE_URL}{endpoint}",
            params=params,
            headers={"User-Agent": NOMINATIM_USER_AGENT},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise NominatimError("Failed to communicate with Nominatim.") from exc

    _CACHE[key] = (now + CACHE_TTL_SECONDS, payload)
    return payload


def geocode_location(query: str) -> Optional[Dict[str, Any]]:
    payload = _request(
        "/search",
        {
            "q": query,
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
        },
    )
    if not payload:
        return None

    item = payload[0]
    return {
        "name": item.get("display_name", query),
        "lat": float(item["lat"]),
        "lon": float(item["lon"]),
    }


def _build_viewbox(lat: float, lon: float, radius_meters: int = 3500) -> str:
    lat_delta = radius_meters / 111_000
    lon_delta = radius_meters / (111_000 * max(0.3, abs(math.cos(math.radians(lat)))))
    left = lon - lon_delta
    right = lon + lon_delta
    top = lat + lat_delta
    bottom = lat - lat_delta
    return f"{left},{top},{right},{bottom}"


def search_candidates(lat: float, lon: float, category: str, limit: int = 30) -> List[Dict[str, Any]]:
    if category not in CATEGORY_TAGS:
        raise NominatimError("Unsupported search category.")

    tag = CATEGORY_TAGS[category]
    params: Dict[str, Any] = {
        "format": "jsonv2",
        "limit": limit,
        "bounded": 1,
        "viewbox": _build_viewbox(lat, lon),
        "addressdetails": 1,
        "extratags": 1,
    }
    params.update(tag)

    payload = _request("/search", params)
    if not isinstance(payload, list):
        raise NominatimError("Unexpected response format from Nominatim.")
    return payload
