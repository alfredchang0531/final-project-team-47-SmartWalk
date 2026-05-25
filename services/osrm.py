import os
from typing import Any, Dict, List, Optional

import requests


class OSRMError(Exception):
    """Raised when OSRM requests fail."""


OSRM_BASE_URL = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")
API_TIMEOUT = float(os.getenv("API_TIMEOUT", "15"))


def _coord(lat: float, lon: float) -> str:
    return f"{lon},{lat}"


def get_walking_matrix(origin: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Optional[float]]]:
    if not candidates:
        return []

    coordinates = [_coord(origin["lat"], origin["lon"])] + [_coord(p["lat"], p["lon"]) for p in candidates]
    coord_str = ";".join(coordinates)
    url = f"{OSRM_BASE_URL}/table/v1/walking/{coord_str}"

    try:
        response = requests.get(
            url,
            params={"annotations": "duration,distance", "sources": "0"},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        raise OSRMError("Failed to fetch walking matrix from OSRM.") from exc

    if payload.get("code") != "Ok":
        raise OSRMError("OSRM matrix request failed.")

    durations = payload.get("durations", [[None]])[0][1:]
    distances = payload.get("distances", [[None]])[0][1:]

    matrix = []
    for duration, distance in zip(durations, distances):
        matrix.append({"duration_sec": duration, "distance_m": distance})
    return matrix


def get_walking_route(origin: Dict[str, Any], destination: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    coord_str = ";".join(
        [
            _coord(origin["lat"], origin["lon"]),
            _coord(destination["lat"], destination["lon"]),
        ]
    )
    url = f"{OSRM_BASE_URL}/route/v1/walking/{coord_str}"

    try:
        response = requests.get(
            url,
            params={"overview": "full", "geometries": "geojson", "steps": "false"},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return None

    if payload.get("code") != "Ok" or not payload.get("routes"):
        return None

    route = payload["routes"][0]
    coordinates = route.get("geometry", {}).get("coordinates", [])
    latlon_geometry = [[lat, lon] for lon, lat in coordinates]

    return {
        "geometry": latlon_geometry,
        "duration_sec": route.get("duration"),
        "distance_m": route.get("distance"),
    }
