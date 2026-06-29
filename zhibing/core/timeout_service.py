"""Upper-layer timeout computation and polling checks."""

from __future__ import annotations

from dataclasses import dataclass


class TimeoutConfigError(ValueError):
    """Raised when timeout factors would make planning unsafe."""


def compute_timeout(
    path_distance_m: float,
    base_speed_mps: float,
    terrain_factor: float = 1.0,
    weather_factor: float = 1.0,
    formation_factor: float = 1.0,
    threat_factor: float = 1.0,
    load_bt_overhead_s: float = 5.0,
    formation_overhead_s: float = 10.0,
    safety_margin_s: float = 30.0,
) -> dict[str, int]:
    factors = (terrain_factor, weather_factor, formation_factor, threat_factor)
    if path_distance_m < 0:
        raise TimeoutConfigError("path_distance_m must be non-negative.")
    if base_speed_mps <= 0 or any(factor <= 0 for factor in factors):
        raise TimeoutConfigError("speed and timeout factors must be positive.")
    effective_speed = base_speed_mps * terrain_factor * weather_factor * formation_factor * threat_factor
    expected_s = path_distance_m / effective_speed + load_bt_overhead_s + formation_overhead_s + safety_margin_s
    hard_timeout_s = max(expected_s * 1.5, expected_s + 60)
    stall_timeout_s = max(60, expected_s * 0.2)
    return {
        "expected_seconds": round(expected_s),
        "hard_timeout_seconds": round(hard_timeout_s),
        "stall_timeout_seconds": round(stall_timeout_s),
    }


@dataclass(frozen=True)
class TimeoutCheck:
    timed_out: bool
    stalled: bool
    reason: str | None = None


class TimeoutService:
    def compute_timeout(self, *args, **kwargs) -> dict[str, int]:
        return compute_timeout(*args, **kwargs)

    def check_poll(
        self,
        *,
        elapsed_seconds: float,
        hard_timeout_seconds: float,
        seconds_since_progress: float,
        stall_timeout_seconds: float,
        progress_rate_mps: float,
    ) -> TimeoutCheck:
        if elapsed_seconds >= hard_timeout_seconds:
            return TimeoutCheck(timed_out=True, stalled=False, reason="TASK_TIMEOUT")
        if seconds_since_progress >= stall_timeout_seconds and progress_rate_mps <= 0:
            return TimeoutCheck(timed_out=False, stalled=True, reason="NO_PROGRESS")
        return TimeoutCheck(timed_out=False, stalled=False)

