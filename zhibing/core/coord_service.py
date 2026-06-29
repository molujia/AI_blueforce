"""Coordinate validation and conversion service.

All upper-layer coordinates must carry an explicit frame. VBS-native numeric
tuples are produced only inside the SQF compiler boundary.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Mapping

from zhibing.config import VBS_ORIGIN_WGS84


VALID_FRAMES = {"WGS84_LATLON_ALT", "VBS_LOCAL_XYZ"}
EARTH_RADIUS_M = 6378137.0


class CoordinateError(ValueError):
    """Raised when a coordinate object violates the protocol."""


@dataclass(frozen=True)
class CoordService:
    """Coordinate conversion service with a local tangent-plane approximation."""

    origin: Mapping[str, float | str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.origin is None:
            object.__setattr__(self, "origin", VBS_ORIGIN_WGS84)
        self.validate(self.origin)

    def validate(self, coord: Any) -> dict[str, float | str]:
        if not isinstance(coord, Mapping):
            raise CoordinateError("CoordinateObject must be an object with a frame field.")
        frame = coord.get("frame")
        if frame not in VALID_FRAMES:
            raise CoordinateError("CoordinateObject frame must be WGS84_LATLON_ALT or VBS_LOCAL_XYZ.")
        if frame == "WGS84_LATLON_ALT":
            required = ("lat", "lon", "alt")
        else:
            required = ("x", "y", "z")
        missing = [name for name in required if name not in coord]
        if missing:
            raise CoordinateError(f"CoordinateObject missing required fields: {', '.join(missing)}")
        clean: dict[str, float | str] = {"frame": str(frame)}
        for name in required:
            value = coord[name]
            if not isinstance(value, (int, float)):
                raise CoordinateError(f"Coordinate field {name} must be numeric.")
            clean[name] = float(value)
        return clean

    def to_vbs_local(self, coord: Mapping[str, Any]) -> dict[str, float | str]:
        clean = self.validate(coord)
        if clean["frame"] == "VBS_LOCAL_XYZ":
            return clean
        origin = self.validate(self.origin)
        lat = math.radians(float(clean["lat"]))
        lon = math.radians(float(clean["lon"]))
        origin_lat = math.radians(float(origin["lat"]))
        origin_lon = math.radians(float(origin["lon"]))
        x = (lon - origin_lon) * math.cos(origin_lat) * EARTH_RADIUS_M
        y = (lat - origin_lat) * EARTH_RADIUS_M
        z = float(clean["alt"]) - float(origin["alt"])
        return {"frame": "VBS_LOCAL_XYZ", "x": x, "y": y, "z": z}

    def to_wgs84(self, coord: Mapping[str, Any]) -> dict[str, float | str]:
        clean = self.validate(coord)
        if clean["frame"] == "WGS84_LATLON_ALT":
            return clean
        origin = self.validate(self.origin)
        origin_lat = math.radians(float(origin["lat"]))
        lat = math.radians(float(origin["lat"])) + float(clean["y"]) / EARTH_RADIUS_M
        lon = math.radians(float(origin["lon"])) + float(clean["x"]) / (math.cos(origin_lat) * EARTH_RADIUS_M)
        alt = float(origin["alt"]) + float(clean["z"])
        return {"frame": "WGS84_LATLON_ALT", "lat": math.degrees(lat), "lon": math.degrees(lon), "alt": alt}

    def distance_m(self, start: Mapping[str, Any], goal: Mapping[str, Any]) -> float:
        s = self.to_vbs_local(start)
        g = self.to_vbs_local(goal)
        dx = float(g["x"]) - float(s["x"])
        dy = float(g["y"]) - float(s["y"])
        dz = float(g["z"]) - float(s["z"])
        return math.sqrt(dx * dx + dy * dy + dz * dz)


default_coord_service = CoordService()

