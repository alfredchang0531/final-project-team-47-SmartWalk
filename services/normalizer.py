from typing import Any, Dict, List, Tuple


def _extract_name(item: Dict[str, Any]) -> str:
    name = item.get("name")
    if name:
        return name.strip()
    display_name = item.get("display_name", "Unknown Place")
    return str(display_name).split(",")[0].strip() or "Unknown Place"


def normalize_candidates(raw_candidates: List[Dict[str, Any]], category: str) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    seen: set[Tuple[str, float, float]] = set()

    for item in raw_candidates:
        try:
            lat = float(item["lat"])
            lon = float(item["lon"])
        except (KeyError, TypeError, ValueError):
            continue

        name = _extract_name(item)
        key = (name.lower(), round(lat, 5), round(lon, 5))
        if key in seen:
            continue
        seen.add(key)

        subtype = item.get("type") or item.get("class") or "unknown"
        normalized.append(
            {
                "id": f"{item.get('osm_type', 'node')}-{item.get('osm_id', name)}",
                "name": name,
                "lat": lat,
                "lon": lon,
                "category": category,
                "subtype": subtype,
                "display_name": item.get("display_name", name),
            }
        )

    return normalized
