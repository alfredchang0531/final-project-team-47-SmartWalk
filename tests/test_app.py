import app as app_module


def test_index_page_loads():
    client = app_module.app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"WalkSmart" in response.data


def test_search_workflow_with_mocked_services(monkeypatch):
    client = app_module.app.test_client()

    monkeypatch.setattr(
        app_module,
        "geocode_location",
        lambda location: {"name": "Test Origin", "lat": 40.0, "lon": -73.0},
    )
    monkeypatch.setattr(
        app_module,
        "search_candidates",
        lambda lat, lon, category: [
            {"lat": "40.001", "lon": "-73.001", "name": "Cafe One", "type": "cafe", "display_name": "Cafe One"},
            {"lat": "40.002", "lon": "-73.002", "name": "Cafe Two", "type": "cafe", "display_name": "Cafe Two"},
        ],
    )
    monkeypatch.setattr(
        app_module,
        "get_walking_matrix",
        lambda origin, candidates: [
            {"duration_sec": 240, "distance_m": 300},
            {"duration_sec": 480, "distance_m": 600},
        ],
    )
    monkeypatch.setattr(
        app_module,
        "get_walking_route",
        lambda origin, destination: {
            "geometry": [[40.0, -73.0], [destination["lat"], destination["lon"]]],
            "duration_sec": destination.get("duration_sec", 0),
            "distance_m": destination.get("distance_m", 0),
        },
    )
    monkeypatch.setattr(app_module, "generate_results_map", lambda origin, places, routes: "<div>mock map</div>")

    response = client.post(
        "/search",
        data={"location": "somewhere", "category": "cafe", "max_time": "10"},
    )

    assert response.status_code == 200
    assert b"WalkSmart Results" in response.data
    assert b"Cafe One" in response.data
    assert b"mock map" in response.data
