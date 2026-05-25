import os
from typing import Any, Dict, List

from flask import Flask, render_template, request

from renderers.map_generator import generate_results_map
from services.nominatim import NominatimError, geocode_location, search_candidates
from services.normalizer import normalize_candidates
from services.osrm import OSRMError, get_walking_matrix, get_walking_route
from services.scoring import calculate_convenience_score, rank_places

CATEGORIES = {
    "cafe": "Cafe",
    "restaurant": "Restaurant",
    "pharmacy": "Pharmacy",
    "convenience_store": "Convenience Store",
    "park": "Park",
}
VALID_WALK_TIMES = {5, 10, 15, 20}


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "walksmart-dev-key")

    @app.route("/", methods=["GET"])
    def index() -> str:
        return render_template(
            "index.html",
            categories=CATEGORIES,
            walk_times=sorted(VALID_WALK_TIMES),
            selected_time=10,
        )

    @app.route("/search", methods=["POST"])
    def search() -> str:
        location = (request.form.get("location") or "").strip()
        category = (request.form.get("category") or "").strip()
        lunch_mode = request.form.get("lunch_mode") == "on"

        try:
            max_time = int(request.form.get("max_time", "10"))
        except ValueError:
            max_time = 10

        if not location:
            return render_template(
                "index.html",
                categories=CATEGORIES,
                walk_times=sorted(VALID_WALK_TIMES),
                selected_time=max_time,
                selected_category=category,
                error="Please enter a starting location.",
            )

        if category not in CATEGORIES:
            return render_template(
                "index.html",
                categories=CATEGORIES,
                walk_times=sorted(VALID_WALK_TIMES),
                selected_time=max_time,
                error="Please select a valid category.",
            )

        if max_time not in VALID_WALK_TIMES:
            max_time = 10

        try:
            origin = geocode_location(location)
            if not origin:
                return render_template(
                    "result.html",
                    error="Starting location not found. Please try a more specific place name.",
                    summary={"origin": location, "category": CATEGORIES[category], "max_time": max_time},
                    places=[],
                    score={"score": 0, "explanation": "No reachable places found."},
                    map_html=None,
                )

            candidate_raw = search_candidates(origin["lat"], origin["lon"], category)
            candidates = normalize_candidates(candidate_raw, category)

            if not candidates:
                return render_template(
                    "result.html",
                    error="No candidate places were found nearby for this category.",
                    summary={
                        "origin": origin["name"],
                        "category": CATEGORIES[category],
                        "max_time": max_time,
                        "reachable_count": 0,
                    },
                    places=[],
                    score={"score": 0, "explanation": "No reachable places found."},
                    map_html=None,
                )

            metrics = get_walking_matrix(origin, candidates)
            max_seconds = max_time * 60
            reachable: List[Dict[str, Any]] = []
            for place, metric in zip(candidates, metrics):
                duration = metric.get("duration_sec")
                distance = metric.get("distance_m")
                if duration is None or distance is None:
                    continue
                if duration <= max_seconds:
                    enriched = {**place, **metric}
                    reachable.append(enriched)

            ranked = rank_places(reachable, lunch_mode=lunch_mode, selected_category=category)
            top_for_routes = ranked[:5]
            routes = []
            for place in top_for_routes:
                route = get_walking_route(origin, place)
                if route:
                    routes.append({"name": place["name"], **route})

            score = calculate_convenience_score(ranked, max_time)
            map_html = generate_results_map(origin, ranked, routes)

            summary = {
                "origin": origin["name"],
                "category": CATEGORIES[category],
                "max_time": max_time,
                "reachable_count": len(ranked),
                "lunch_mode": lunch_mode,
            }

            if not ranked:
                return render_template(
                    "result.html",
                    error="No places are reachable within your selected walking time.",
                    summary=summary,
                    places=[],
                    score=score,
                    map_html=map_html,
                )

            return render_template(
                "result.html",
                summary=summary,
                places=ranked,
                score=score,
                map_html=map_html,
                error=None,
            )
        except (NominatimError, OSRMError) as exc:
            return render_template(
                "result.html",
                error=f"Service error: {exc}",
                summary={"origin": location, "category": CATEGORIES.get(category, category), "max_time": max_time},
                places=[],
                score={"score": 0, "explanation": "Unable to calculate score due to service error."},
                map_html=None,
            )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
