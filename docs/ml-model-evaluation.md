# Model evaluation

The energy and comfort `RandomForestRegressor` models report MAE, RMSE and R².
Occupancy and cooling `RandomForestClassifier` models report accuracy,
weighted precision, weighted recall and weighted F1. Anomaly detection uses an
`IsolationForest` over load, historical average, runtime, time and AC load;
its report is qualitative because it is unsupervised.

These numbers are generated from synthetic, correlated simulator data and
should only be used to validate wiring and regression behavior. They are not
real-world model-performance estimates.
