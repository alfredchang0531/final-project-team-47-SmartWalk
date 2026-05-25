# WalkSmart

WalkSmart is a Flask web application that finds useful places reachable within a selected walking time using Nominatim + OSRM, then displays ranked results and routes on an interactive Folium (Leaflet) map.

## Features

- Natural-language origin input
- Category search: cafe, restaurant, pharmacy, convenience store, park
- Walking-time filter: 5 / 10 / 15 / 20 minutes
- Nominatim geocoding + candidate POI search
- OSRM Table walking duration/distance filtering
- OSRM Route geometry for top results
- WalkSmart Convenience Score (0-100)
- Optional Lunch Mode for cafe/restaurant ranking bias
- Error handling for location/candidate/route failures
- In-memory TTL cache + request throttling for Nominatim

## Project Structure

- `app.py`
- `services/nominatim.py`
- `services/osrm.py`
- `services/normalizer.py`
- `services/scoring.py`
- `renderers/map_generator.py`
- `templates/index.html`
- `templates/result.html`
- `static/style.css`
- `tests/`

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Or:

```bash
export FLASK_APP=app
flask run
```

Open <http://127.0.0.1:5000>.

## Environment Variables

- `NOMINATIM_BASE_URL` (default `https://nominatim.openstreetmap.org`)
- `NOMINATIM_USER_AGENT` (default WalkSmart UA string)
- `NOMINATIM_CACHE_TTL` (default `300` seconds)
- `NOMINATIM_MIN_INTERVAL` (default `1.0` seconds)
- `OSRM_BASE_URL` (default `https://router.project-osrm.org`)
- `API_TIMEOUT` (default `15` seconds)
- `SECRET_KEY` (default development key)

## Testing

```bash
python -m pytest -q
```
