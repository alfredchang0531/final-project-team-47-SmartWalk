from __future__ import annotations

from flask import Flask, render_template, request

from walksmart import (
    CATEGORY_TO_AMENITY,
    build_map,
    compute_convenience_score,
    geocode_start_location,
    rank_places_with_walk_time,
    search_candidate_places,
)

app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    categories = list(CATEGORY_TO_AMENITY.keys())
    context = {
        "categories": categories,
        "selected_category": categories[0],
        "max_minutes": 15,
        "start_query": "",
        "results": [],
        "map_html": None,
        "score": None,
        "error": None,
    }

    if request.method == "POST":
        start_query = request.form.get("start_location", "").strip()
        selected_category = request.form.get("category", categories[0])
        max_minutes = int(request.form.get("max_minutes", 15))
        max_minutes = max(1, min(max_minutes, 120))

        context.update(
            {
                "selected_category": selected_category,
                "max_minutes": max_minutes,
                "start_query": start_query,
            }
        )

        start = geocode_start_location(start_query)
        if not start:
            context["error"] = "Could not find that starting location. Please try another query."
            return render_template("index.html", **context)

        candidates = search_candidate_places(start["lat"], start["lon"], selected_category)
        ranked = rank_places_with_walk_time(start["lat"], start["lon"], candidates, max_minutes)
        context["results"] = ranked
        context["score"] = compute_convenience_score(ranked, max_minutes)
        context["map_html"] = build_map(start, ranked)

        if not ranked:
            context["error"] = (
                "No places matched your walking-time limit. "
                "Try increasing the limit or changing category."
            )

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True)
