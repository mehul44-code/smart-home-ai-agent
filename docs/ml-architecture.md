# Lightweight ML architecture

Prompt 5 adds a deliberately small, local ML layer. `generate_training_data`
uses correlated simulator-style telemetry (thermal, occupancy, tariff, load and
runtime) with a fixed seed. `train_all_models` writes versioned, compressed
joblib artifacts to `backend/models`: energy and comfort regressors, occupancy
and cooling classifiers, and an IsolationForest anomaly detector.

`MLModelManager` validates every artifact before loading. `PredictionEngine`
uses available models independently, so one missing or incompatible file does
not disable the agent. Missing predictions retain the Prompt 4 deterministic
thermal/comfort/utility behavior and are marked `prediction_source:
BASELINE_FALLBACK`; model-backed results are marked `ML`.

