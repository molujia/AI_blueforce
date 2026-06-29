import unittest
from zhibing.core.timeout_service import TimeoutConfigError, compute_timeout


class TimeoutServiceTests(unittest.TestCase):
    def test_compute_timeout_uses_formula(self) -> None:
        result = compute_timeout(path_distance_m=1000.0, base_speed_mps=10.0, terrain_factor=1.0, weather_factor=1.0, formation_factor=1.0, threat_factor=1.0)
        self.assertEqual(result["expected_seconds"], 145)
        self.assertEqual(result["hard_timeout_seconds"], 218)
        self.assertEqual(result["stall_timeout_seconds"], 60)

    def test_compute_timeout_rejects_zero_speed(self) -> None:
        with self.assertRaises(TimeoutConfigError):
            compute_timeout(path_distance_m=100.0, base_speed_mps=0.0)


if __name__ == "__main__":
    unittest.main()
