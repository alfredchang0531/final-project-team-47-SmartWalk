import walksmart


def test_compute_convenience_score_no_results():
    score = walksmart.compute_convenience_score([], 15)
    assert score["score"] == 0
    assert score["label"] == "Low convenience"


def test_compute_convenience_score_with_results():
    results = [
        {"duration_min": 5.0},
        {"duration_min": 7.0},
        {"duration_min": 10.0},
    ]
    score = walksmart.compute_convenience_score(results, 15)
    assert 0 < score["score"] <= 100
    assert "reachable place(s)" in score["summary"]


def test_rank_places_with_walk_time_filters_and_sorts(monkeypatch):
    candidates = [
        {"name": "B Place", "display_name": "B", "lat": 1.0, "lon": 1.0},
        {"name": "A Place", "display_name": "A", "lat": 2.0, "lon": 2.0},
        {"name": "Far Place", "display_name": "F", "lat": 3.0, "lon": 3.0},
    ]

    route_by_destination = {
        (1.0, 1.0): {"duration_sec": 600.0, "distance_m": 700.0, "geometry": {}},
        (2.0, 2.0): {"duration_sec": 300.0, "distance_m": 500.0, "geometry": {}},
        (3.0, 3.0): {"duration_sec": 2500.0, "distance_m": 3000.0, "geometry": {}},
    }

    def fake_route(start_lat, start_lon, end_lat, end_lon):
        return route_by_destination[(end_lat, end_lon)]

    monkeypatch.setattr(walksmart, "get_walking_route", fake_route)

    ranked = walksmart.rank_places_with_walk_time(0.0, 0.0, candidates, max_minutes=15)
    assert [item["name"] for item in ranked] == ["A Place", "B Place"]
    assert all(item["duration_sec"] <= 900 for item in ranked)
    assert "Rank #1:" in ranked[0]["explanation"]
