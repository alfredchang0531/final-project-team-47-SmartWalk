from services.normalizer import normalize_candidates
from services.scoring import calculate_convenience_score, rank_places


def test_normalize_candidates_deduplicates_and_skips_invalid():
    raw = [
        {"lat": "40.0", "lon": "-73.0", "name": "Cafe A", "type": "cafe", "osm_type": "node", "osm_id": 1},
        {"lat": "40.0", "lon": "-73.0", "name": "Cafe A", "type": "cafe", "osm_type": "node", "osm_id": 1},
        {"lat": "invalid", "lon": "-73.1", "name": "Bad"},
    ]

    result = normalize_candidates(raw, "cafe")

    assert len(result) == 1
    assert result[0]["name"] == "Cafe A"
    assert result[0]["category"] == "cafe"


def test_scoring_returns_zero_for_empty_result():
    score = calculate_convenience_score([], 10)
    assert score["score"] == 0


def test_rank_places_sorts_by_duration_default():
    places = [
        {"name": "A", "duration_sec": 600, "distance_m": 800, "display_name": "A", "subtype": "cafe"},
        {"name": "B", "duration_sec": 300, "distance_m": 700, "display_name": "B", "subtype": "cafe"},
    ]

    ranked = rank_places(places)
    assert ranked[0]["name"] == "B"
    assert "Rank #1" in ranked[0]["explanation"]
