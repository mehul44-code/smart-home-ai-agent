"""Reproducible, simulator-correlated training data for the lightweight ML layer."""
from __future__ import annotations

import os
from typing import Optional

import numpy as np
import pandas as pd


def generate_training_data(
    num_samples: int = 1500, seed: int = 42, output_path: Optional[str] = None
) -> pd.DataFrame:
    """Generate correlated home telemetry and labels without mutating the simulator.

    The equations mirror the simulator's thermal/load relationships.  A fixed
    local RNG makes repeated calls byte-for-byte reproducible.
    """
    rng = np.random.default_rng(seed)
    minutes = rng.uniform(0, 24 * 60, num_samples)
    hour = minutes / 60
    indoor = rng.normal(24.2, 2.1, num_samples).clip(18, 32)
    outdoor = (27 + 6 * np.sin((hour - 8) * np.pi / 12) + rng.normal(0, .8, num_samples))
    occupancy = ((rng.random(num_samples) < (0.25 + .5 * ((hour >= 7) & (hour <= 22)))).astype(int))
    occupant_count = occupancy * rng.integers(1, 4, num_samples)
    humidity = (55 + (outdoor - 25) * 1.2 + rng.normal(0, 4, num_samples)).clip(20, 90)
    ac_power = np.where(indoor > 24.5, rng.choice([0, 1.2, 1.9], num_samples), 0)
    base_load = 0.35 + occupant_count * .12 + rng.normal(0, .04, num_samples)
    total_load = np.maximum(.05, base_load + ac_power + rng.choice([0, .1, .8], num_samples, p=[.55, .3, .15]))
    target = 22 + rng.normal(0, .3, num_samples)
    tariff = np.where((hour >= 17) & (hour < 22), 12., np.where((hour < 7) | (hour >= 23), 4., 8.))
    runtime = np.maximum(0, ac_power > .1).astype(float) * rng.uniform(5, 180, num_samples)
    historical_avg = np.maximum(.1, total_load * rng.normal(1, .08, num_samples))
    temp_delta = ((outdoor - indoor) / 2.5 + np.where(occupancy, .24, .05) - ac_power * 3.2) / 18 * .25
    temp_delta += rng.normal(0, .03, num_samples)
    energy = np.maximum(0, ac_power * .25 + np.maximum(0, indoor - target) * 18 / 3.2 / 100)
    comfort = np.clip(100 - np.abs(indoor - target) * 15 - np.maximum(0, humidity - 65) * .25, 0, 100)
    cooling = np.select([indoor <= target + .5, indoor <= target + 2], ["LOW", "MEDIUM"], default="HIGH")
    anomaly = ((total_load > historical_avg * 1.35) | (runtime > 160) | (total_load > 5)).astype(int)
    df = pd.DataFrame({
        "hour": hour, "indoor_temp_c": indoor, "outdoor_temp_c": outdoor,
        "humidity_pct": humidity, "occupancy": occupancy, "occupant_count": occupant_count,
        "ac_power_kw": ac_power, "total_load_kw": total_load, "historical_average_kw": historical_avg,
        "power_kw": total_load,
        "runtime_minutes": runtime, "target_temp_c": target, "tariff_rate": tariff,
        "temp_delta_c": temp_delta, "energy_kwh": energy, "comfort_score": comfort,
        "cooling_level": cooling, "anomaly": anomaly,
        "actual_load_kw": total_load,
    }).round(5)
    if output_path:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        df.to_csv(output_path, index=False)
    return df


def generate_synthetic_thermal_data(num_samples: int = 1000, output_path: str = "data/raw/synthetic_thermal_history.csv"):
    """Backward-compatible thermal-only export used by Prompt 3 tooling."""
    return generate_training_data(num_samples, 42, output_path)[
        ["indoor_temp_c", "outdoor_temp_c", "ac_power_kw", "occupancy", "temp_delta_c"]
    ].assign(horizon_minutes=15.0)


if __name__ == "__main__":
    generate_training_data(output_path="data/raw/synthetic_training_data.csv")
