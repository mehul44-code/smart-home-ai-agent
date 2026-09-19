import json

from backend.app.agent.perception import PerceptionEngine
from backend.app.agent.prediction import PredictionEngine
from backend.app.ml.model_loader import MLModelManager
from backend.app.simulator.home_simulator import simulator_instance
from backend.training.sample_data_generator import generate_training_data
from backend.training.train import train_all_models


def test_generator_is_reproducible():
    assert generate_training_data(20, 7).equals(generate_training_data(20, 7))


def test_generator_has_correlated_training_contract():
    data = generate_training_data(30)
    assert {"total_load_kw", "historical_average_kw", "runtime_minutes", "energy_kwh",
            "comfort_score", "cooling_level", "anomaly"} <= set(data.columns)


def test_training_writes_all_compact_artifacts(tmp_path):
    report = train_all_models(str(tmp_path), 120, 3)
    assert {"energy_model", "occupancy_model", "cooling_model", "comfort_model", "anomaly_model"} <= set(report["models"])
    assert (tmp_path / "metrics.json").exists()
    assert len(list(tmp_path.glob("*.joblib"))) == 5


def test_training_metrics_have_required_regression_metrics(tmp_path):
    report = train_all_models(str(tmp_path), 100, 4)
    assert {"MAE", "RMSE", "R2"} <= set(report["models"]["energy_model"])
    assert {"MAE", "RMSE"} <= set(report["models"]["comfort_model"])


def test_training_metrics_have_required_classification_metrics(tmp_path):
    report = train_all_models(str(tmp_path), 100, 4)
    assert {"accuracy", "precision", "recall", "F1"} <= set(report["models"]["occupancy_model"])
    assert {"accuracy", "precision", "recall", "F1"} <= set(report["models"]["cooling_model"])


def test_loader_missing_directory_falls_back(tmp_path):
    manager = MLModelManager(str(tmp_path))
    assert not manager.available("energy")
    assert manager.predict("energy", {}) is None


def test_loader_corrupt_artifact_is_safe(tmp_path):
    (tmp_path / "energy_model.joblib").write_bytes(b"not a joblib")
    manager = MLModelManager(str(tmp_path))
    assert not manager.available("energy")
    assert "energy" in manager.load_errors


def test_loader_loads_and_infers_models(tmp_path):
    train_all_models(str(tmp_path), 100, 5)
    manager = MLModelManager(str(tmp_path))
    assert manager.available("comfort")
    assert 0 <= float(manager.predict("comfort", {})) <= 100


def test_prediction_marks_baseline_fallback(tmp_path):
    percept = PerceptionEngine().observe(simulator_instance.get_current_home_state())
    result = PredictionEngine(model_manager=MLModelManager(str(tmp_path))).predict(percept)
    assert result["prediction_source"] == "BASELINE_FALLBACK"


def test_prediction_uses_trained_models(tmp_path):
    train_all_models(str(tmp_path), 120, 6)
    percept = PerceptionEngine().observe(simulator_instance.get_current_home_state())
    result = PredictionEngine(model_manager=MLModelManager(str(tmp_path))).predict(percept)
    assert result["prediction_source"] == "ML"
    assert "cooling_level" in result
    assert 0 <= result["comfort_score"] <= 100


def test_anomaly_contract(tmp_path):
    train_all_models(str(tmp_path), 120, 6)
    manager = MLModelManager(str(tmp_path))
    result = manager.predict_anomaly({"power_kw": 3, "total_load_kw": 3,
                                      "historical_average_kw": 1, "runtime_minutes": 200, "hour": 18})
    assert {"anomaly", "score", "expected", "actual", "severity"} <= set(result)
