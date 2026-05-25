from typing import Any, Dict, List

import folium


def generate_results_map(origin: Dict[str, Any], places: List[Dict[str, Any]], routes: List[Dict[str, Any]]) -> str:
    center = [origin["lat"], origin["lon"]]
    fmap = folium.Map(location=center, zoom_start=14, tiles="OpenStreetMap")

    folium.Marker(
        center,
        popup=f"Origin: {origin['name']}",
        icon=folium.Icon(color="blue", icon="home"),
    ).add_to(fmap)

    bounds = [center]
    for place in places:
        point = [place["lat"], place["lon"]]
        bounds.append(point)
        duration = round(float(place.get("duration_sec", 0)) / 60)
        distance = float(place.get("distance_m", 0)) / 1000
        popup = f"{place['name']}<br>{duration} min • {distance:.2f} km"
        folium.Marker(point, popup=popup, icon=folium.Icon(color="green", icon="ok-sign")).add_to(fmap)

    for route in routes:
        geometry = route.get("geometry") or []
        if not geometry:
            continue
        folium.PolyLine(geometry, weight=4, opacity=0.7, tooltip=route.get("name", "Route")).add_to(fmap)

    if len(bounds) > 1:
        fmap.fit_bounds(bounds)

    return fmap._repr_html_()
