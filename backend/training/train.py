import os
import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from backend.training.sample_data_generator import generate_synthetic_thermal_data


def train_thermal_model():
    """
    Trains a scikit-learn Random Forest regressor to predict indoor thermal drift
    and saves the model artifact to backend/models/thermal_model.joblib.
    """
    data_path = "data/raw/synthetic_thermal_history.csv"
    if not os.path.exists(data_path):
        df = generate_synthetic_thermal_data(output_path=data_path)
    else:
        df = pd.read_csv(data_path)

    features = ["indoor_temp_c", "outdoor_temp_c", "ac_power_kw", "occupancy", "horizon_minutes"]
    target = "temp_delta_c"

    X = df[features]
    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    mse = mean_squared_error(y_test, predictions)
    r2 = r2_score(y_test, predictions)

    print(f"Model Training Complete! Test MSE: {mse:.4f}, R2 Score: {r2:.4f}")

    models_dir = os.path.join(os.path.dirname(__file__), "..", "models")
    os.makedirs(models_dir, exist_ok=True)
    out_file = os.path.join(models_dir, "thermal_model.joblib")
    joblib.dump(model, out_file)
    print(f"Model successfully saved to {out_file}")


if __name__ == "__main__":
    train_thermal_model()
