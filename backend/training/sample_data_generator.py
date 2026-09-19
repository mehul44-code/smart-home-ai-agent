import numpy as np
import pandas as pd
import os

def generate_synthetic_thermal_data(num_samples: int = 1000, output_path: str = "data/raw/synthetic_thermal_history.csv"):
    """
    Generates realistic synthetic thermal and power telemetry data
    for training the thermal drift ML prediction model.
    """
    np.random.seed(42)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Features
    indoor_temp = np.random.uniform(20.0, 28.0, size=num_samples)
    outdoor_temp = np.random.uniform(18.0, 38.0, size=num_samples)
    ac_power_kw = np.random.choice([0.0, 1.2, 1.9, 2.5], size=num_samples)
    occupancy = np.random.choice([0, 1], size=num_samples, p=[0.4, 0.6])
    horizon_minutes = np.full(num_samples, 15.0)

    # Thermodynamic target: dT = ((T_out - T_in)/2.5 + Q_int - Q_cool)/18.0 * (15/60) + noise
    q_env = (outdoor_temp - indoor_temp) / 2.5
    q_int = np.where(occupancy == 1, 0.24, 0.05)
    q_cool = ac_power_kw * 3.2
    noise = np.random.normal(0, 0.04, size=num_samples)

    temp_delta_c = ((q_env + q_int - q_cool) / 18.0) * (horizon_minutes / 60.0) + noise

    df = pd.DataFrame({
        "indoor_temp_c": np.round(indoor_temp, 2),
        "outdoor_temp_c": np.round(outdoor_temp, 2),
        "ac_power_kw": np.round(ac_power_kw, 2),
        "occupancy": occupancy,
        "horizon_minutes": horizon_minutes,
        "temp_delta_c": np.round(temp_delta_c, 3)
    })

    df.to_csv(output_path, index=False)
    print(f"Generated {num_samples} samples saved to {output_path}")
    return df

if __name__ == "__main__":
    generate_synthetic_thermal_data()
