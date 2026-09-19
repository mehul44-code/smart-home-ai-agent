# Training

From the repository root:

```powershell
python -m backend.training.train --samples 1500 --seed 42 --output-dir backend/models
```

The generator is reproducible (`generate_training_data(seed=42)`), and the
data is synthetic simulator validation data, not a claim about real homes.
`metrics.json` records the held-out metrics. Artifacts are intentionally
gitignored; tests can pass a temporary output directory to `train_all_models`.

