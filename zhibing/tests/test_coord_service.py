import math
import unittest

from zhibing.core.coord_service import CoordService, CoordinateError


class CoordServiceTests(unittest.TestCase):
    def test_rejects_missing_frame(self) -> None:
        service = CoordService()
        with self.assertRaises(CoordinateError):
            service.validate({"x": 1.0, "y": 2.0, "z": 3.0})

    def test_round_trip_wgs84_to_vbs(self) -> None:
        service = CoordService()
        original = {"frame": "WGS84_LATLON_ALT", "lat": 40.241, "lon": 116.118, "alt": 125.0}
        local = service.to_vbs_local(original)
        restored = service.to_wgs84(local)
        self.assertEqual(local["frame"], "VBS_LOCAL_XYZ")
        self.assertTrue(math.isclose(float(restored["lat"]), original["lat"], rel_tol=0, abs_tol=1e-6))
        self.assertTrue(math.isclose(float(restored["lon"]), original["lon"], rel_tol=0, abs_tol=1e-6))


if __name__ == "__main__":
    unittest.main()
