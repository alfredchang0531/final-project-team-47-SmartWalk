from __future__ import annotations

from statistics import mean

import folium
import requests

NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
OSRM_ROUTE_URL = "https://router.project-osrm.org/route/v1/foot"
REQUEST_HEADERS = {"User-Agent": "WalkSmart/1.0"}
NOMINATIM_RESPONSE_FORMAT = "jsonv2"
SEARCH_VIEWBOX_DELTA_DEGREES = 0.03
MAX_SPEED_SCORE = 35
CLOSE_PROXIMITY_BONUS = 15
CLOSE_PROXIMITY_THRESHOLD_MIN = 8
MAX_ROUTES_TO_DISPLAY = 3

CATEGORY_TO_AMENITY = {
    "cafe": "cafe",
    "restaurant": "restaurant",
    "pharmacy": "pharmacy",
    "convenience store": "convenience",
    "park": "park",
}


def geocode_start_location(query: str) -> dict | None:
    if not query.strip():
        return None
    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={"q": query, "format": NOMINATIM_RESPONSE_FORMAT, "limit": 1},
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        places = response.json()
    except requests.RequestException:
        return None

    if not places:
        return None
    first = places[0]
    return {
        "name": first.get("display_name", query),
        "lat": float(first["lat"]),
        "lon": float(first["lon"]),
    }


def search_candidate_places(start_lat: float, start_lon: float, category: str) -> list[dict]:
    amenity = CATEGORY_TO_AMENITY.get(category, category)
    delta = SEARCH_VIEWBOX_DELTA_DEGREES
    viewbox = (
        f"{start_lon - delta},{start_lat + delta},{start_lon + delta},{start_lat - delta}"
    )
    try:
        response = requests.get(
            NOMINATIM_SEARCH_URL,
            params={
                "q": amenity,
                "amenity": amenity,
                "format": NOMINATIM_RESPONSE_FORMAT,
                "limit": 25,
                "bounded": 1,
                "viewbox": viewbox,
                "addressdetails": 1,
            },
            headers=REQUEST_HEADERS,
            timeout=10,
        )
        response.raise_for_status()
        raw_places = response.json()
    except requests.RequestException:
        return []

    candidates = []
    seen = set()
    for place in raw_places:
        key = (place.get("display_name"), place.get("lat"), place.get("lon"))
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            {
                "name": place.get("name") or place.get("display_name", "Unknown place"),
                "display_name": place.get("display_name", "Unknown place"),
                "lat": float(place["lat"]),
                "lon": float(place["lon"]),
            }
        )
    return candidates


def get_walking_route(
    start_lat: float, start_lon: float, end_lat: float, end_lon: float
) -> dict | None:
    route_url = f"{OSRM_ROUTE_URL}/{start_lon},{start_lat};{end_lon},{end_lat}"
    try:
        response = requests.get(
            route_url, params={"overview": "full", "geometries": "geojson"}, timeout=10
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        return None

    routes = payload.get("routes") or []
    if not routes:
        return None
    route = routes[0]
    return {
        "duration_sec": float(route["duration"]),
        "distance_m": float(route["distance"]),
        "geometry": route.get("geometry", {}),
    }


def recommendation_explanation(place: dict, max_minutes: int, rank: int) -> str:
    return (
        f"Rank #{rank}: about {place['duration_min']:.1f} minutes "
        f"({place['distance_km']:.2f} km), within your {max_minutes}-minute walk."
    )


def rank_places_with_walk_time(
    start_lat: float, start_lon: float, candidates: list[dict], max_minutes: int
) -> list[dict]:
    max_duration_sec = max_minutes * 60
    ranked = []
    for candidate in candidates:
        route = get_walking_route(start_lat, start_lon, candidate["lat"], candidate["lon"])
        if not route:
            continue
        if route["duration_sec"] > max_duration_sec:
            continue
        ranked.append(
            {
                **candidate,
                "duration_sec": route["duration_sec"],
                "duration_min": route["duration_sec"] / 60.0,
                "distance_m": route["distance_m"],
                "distance_km": route["distance_m"] / 1000.0,
                "geometry": route["geometry"],
            }
        )

    ranked.sort(key=lambda item: (item["duration_sec"], item["distance_m"], item["name"]))
    for idx, place in enumerate(ranked, start=1):
        place["explanation"] = recommendation_explanation(place, max_minutes, idx)
    return ranked


def compute_convenience_score(results: list[dict], max_minutes: int) -> dict:
    if not results:
        return {
            "score": 0,
            "label": "Low convenience",
            "summary": "No reachable places were found within the selected walking-time limit.",
        }

    avg_minutes = mean(place["duration_min"] for place in results)
    count_score = min(50, len(results) * 10)
    speed_score = max(
        0, int(MAX_SPEED_SCORE - (avg_minutes / max(max_minutes, 1)) * MAX_SPEED_SCORE)
    )
    close_bonus = (
        CLOSE_PROXIMITY_BONUS
        if any(place["duration_min"] <= CLOSE_PROXIMITY_THRESHOLD_MIN for place in results)
        else 0
    )
    score = min(100, count_score + speed_score + close_bonus)

    if score >= 80:
        label = "Excellent convenience"
    elif score >= 60:
        label = "Good convenience"
    elif score >= 40:
        label = "Fair convenience"
    else:
        label = "Low convenience"

    summary = (
        f"{len(results)} reachable place(s), average walk {avg_minutes:.1f} minutes. "
        f"Shorter average routes and more options increase this score."
    )
    return {"score": score, "label": label, "summary": summary}


def build_map(start: dict, results: list[dict]) -> str:
    start_position = [start["lat"], start["lon"]]
    base_map = folium.Map(location=start_position, zoom_start=15, control_scale=True)

    folium.Marker(
        location=start_position,
        popup=f"Start: {start['name']}",
        tooltip="Starting point",
        icon=folium.Icon(color="blue", icon="home"),
    ).add_to(base_map)

    for idx, place in enumerate(results, start=1):
        folium.Marker(
            location=[place["lat"], place["lon"]],
            popup=(
                f"#{idx} {place['name']}<br>"
                f"{place['duration_min']:.1f} min · {place['distance_km']:.2f} km"
            ),
            tooltip=f"#{idx} {place['name']}",
            icon=folium.Icon(color="green", icon="ok-sign"),
        ).add_to(base_map)

        if idx <= MAX_ROUTES_TO_DISPLAY and place.get("geometry", {}).get("coordinates"):
            points = [[lat, lon] for lon, lat in place["geometry"]["coordinates"]]
            folium.PolyLine(points, color="red", weight=4, opacity=0.7).add_to(base_map)

    return base_map.get_root().render()
