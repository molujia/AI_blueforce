"""Static map asset paths used by the lightweight web UI."""

from __future__ import annotations

from pathlib import Path


VISUALIZATION_STATIC_DIR = Path(__file__).resolve().parents[1] / "web" / "command_ui" / "static" / "command_ui"
LEAFLET_JS = VISUALIZATION_STATIC_DIR / "vendor" / "leaflet.js"
LEAFLET_CSS = VISUALIZATION_STATIC_DIR / "vendor" / "leaflet.css"
ROADS_GEOJSON = VISUALIZATION_STATIC_DIR / "map" / "roads.geojson"
BUILDINGS_GEOJSON = VISUALIZATION_STATIC_DIR / "map" / "buildings.geojson"