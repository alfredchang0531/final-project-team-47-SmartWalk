import app as walksmart_app


def test_index_get():
    client = walksmart_app.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"WalkSmart" in response.data


def test_index_post_invalid_location(monkeypatch):
    monkeypatch.setattr(walksmart_app, "geocode_start_location", lambda query: None)

    client = walksmart_app.app.test_client()
    response = client.post(
        "/",
        data={"start_location": "Unknown Place", "category": "cafe", "max_minutes": "15"},
    )
    assert response.status_code == 200
    assert b"Could not find that starting location" in response.data


def test_index_post_success(monkeypatch):
    monkeypatch.setattr(
        walksmart_app,
        "geocode_start_location",
        lambda query: {"name": "Start", "lat": 25.0, "lon": 121.0},
    )
    monkeypatch.setattr(
        walksmart_app,
        "search_candidate_places",
        lambda lat, lon, category: [{"name": "Cafe A", "lat": 25.01, "lon": 121.01}],
    )
    monkeypatch.setattr(
        walksmart_app,
        "rank_places_with_walk_time",
        lambda *args, **kwargs: [
            {
                "name": "Cafe A",
                "duration_min": 7.0,
                "distance_km": 0.6,
                "explanation": "Rank #1: sample",
            }
        ],
    )
    monkeypatch.setattr(
        walksmart_app,
        "compute_convenience_score",
        lambda results, max_minutes: {
            "score": 70,
            "label": "Good convenience",
            "summary": "1 reachable place(s), average walk 7.0 minutes.",
        },
    )
    monkeypatch.setattr(walksmart_app, "build_map", lambda start, results: "<div>fake-map</div>")

    client = walksmart_app.app.test_client()
    response = client.post(
        "/",
        data={"start_location": "Taipei Main Station", "category": "cafe", "max_minutes": "15"},
    )
    assert response.status_code == 200
    assert b"WalkSmart Convenience Score: 70/100" in response.data
    assert b"Cafe A" in response.data
    assert b"fake-map" in response.data


def test_index_post_invalid_max_minutes():
    client = walksmart_app.app.test_client()
    response = client.post(
        "/",
        data={"start_location": "Taipei Main Station", "category": "cafe", "max_minutes": "abc"},
    )
    assert response.status_code == 200
    assert b"Invalid walking time value" in response.data
