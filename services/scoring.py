from statistics import mean
from typing import Any, Dict, List


def _norm(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return max(0.0, min(1.0, value / max_value))


def rank_places(places: List[Dict[str, Any]], lunch_mode: bool = False, selected_category: str = "") -> List[Dict[str, Any]]:
    def sort_key(place: Dict[str, Any]) -> tuple[float, float]:
        duration = float(place.get("duration_sec", 9_999_999))
        if lunch_mode and selected_category in {"restaurant", "cafe"}:
            comfort_target = 8 * 60
            return (abs(duration - comfort_target), duration)
        return (duration, float(place.get("distance_m", 9_999_999)))

    ranked = sorted(places, key=sort_key)

    for idx, place in enumerate(ranked, start=1):
        walk_min = round(float(place["duration_sec"]) / 60)
        distance_km = float(place["distance_m"]) / 1000
        explanation = f"Rank #{idx}: about {walk_min} min walk ({distance_km:.2f} km)."
        if lunch_mode and selected_category in {"restaurant", "cafe"}:
            explanation += " Lunch Mode prioritizes comfortable short breaks."
        place["explanation"] = explanation

    return ranked


def calculate_convenience_score(places: List[Dict[str, Any]], max_time_minutes: int) -> Dict[str, Any]:
    if not places:
        return {
            "score": 0,
            "explanation": "No reachable places, so the convenience score is 0.",
        }

    count = len(places)
    avg_time = mean(float(p["duration_sec"]) for p in places)
    subtype_diversity = len({p.get("subtype", "unknown") for p in places})

    count_component = _norm(count, 10)
    time_component = 1 - _norm(avg_time, max_time_minutes * 60)
    diversity_component = _norm(subtype_diversity, 5)

    score = round((0.45 * count_component + 0.35 * time_component + 0.20 * diversity_component) * 100)
    score = max(0, min(100, score))

    explanation = (
        f"Score {score}/100 = count({count_component:.2f})*45% + "
        f"time({time_component:.2f})*35% + subtype diversity({diversity_component:.2f})*20%."
    )

    return {
        "score": score,
        "explanation": explanation,
        "components": {
            "reachable_count": count,
            "avg_time_minutes": round(avg_time / 60, 1),
            "subtype_diversity": subtype_diversity,
        },
    }
