# Prompt 5 ML audit

## Existing prediction interface

`backend/app/agent/prediction.py` exposes `PredictionEngine.predict(percept)`.
Prompt 4 currently returns deterministic baseline values for thermal drift,
cooling energy, comfort, occupancy, and anomaly score. It accepts an optional
callable predictor, but the default is not connected to trained model
artifacts. `AutonomousAgent` consumes this result without changing the
utility/decision engine.

## Existing model loader

`backend/app/ml/model_loader.py` defines `MLModelManager`, which attempts to
load `thermal_model.joblib` and `load_model.joblib`. It silently falls back to
physics heuristics for thermal delta and has no interfaces for energy,
occupancy, cooling class, comfort, or anomaly detection. The existing thermal
artifact is a legacy model and is not yet integrated with Prompt 4's
`PredictionEngine`.

## Existing training code

`backend/training/sample_data_generator.py` creates independent thermal
columns and a thermal-delta target. `backend/training/train.py` trains only a
thermal `RandomForestRegressor` and reports MSE/R². No simulator-driven
multi-signal dataset, model registry, evaluation report, or reproducible
all-model training command exists.

## Existing storage and tests

`backend/models/` contains `.gitkeep` and a legacy ignored thermal artifact.
The requirements already include pandas, NumPy, scikit-learn, and joblib.
Prompt 4 tests verify the injectable predictor contract, but no ML training,
loading, fallback, or agent/ML integration tests exist.

## Required additions

- Generate reproducible, simulator-derived correlated training data.
- Train compact energy, occupancy, cooling, comfort, and anomaly models with
  task-appropriate metrics and joblib artifacts.
- Extend the existing loader rather than creating a second architecture.
- Add safe missing/corrupt/incompatible artifact fallback.
- Have `PredictionEngine` use loaded ML predictors when available and label
  every output `prediction_source="ML"` or `"BASELINE_FALLBACK"`.
- Preserve Prompt 4 deterministic comfort behavior and utility/decision logic.
- Add training/evaluation documentation and regression tests.

## Integration flow

```text
simulator HomeState
  -> Prompt 4 perception
  -> MLModelManager predictors (or baseline fallback)
  -> existing candidate/utility/decision/action loop
  -> feedback and Prompt 3 persistence
```

Synthetic metrics must be documented as simulation-generated validation, not
real-world performance.
