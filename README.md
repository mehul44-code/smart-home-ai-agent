# Smart Home AI Agent

This repository contains the Prompt 2 smart-home simulator, the Prompt 3
database/API integration, and the Prompt 4 autonomous agent with the Prompt 5
lightweight ML prediction layer. Prompt 3 stores history and user-supplied
records; the simulator remains the source of truth for current state. The
dashboard and future trained production models are intentionally out of scope.

## Start the backend

From the repository root:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload
```

The SQLite URL is configurable with `DATABASE_URL`, for example
`sqlite+aiosqlite:///./data/smart_home.db`. Tables are created automatically
on application startup.

## API

Interactive OpenAPI documentation is available at `http://127.0.0.1:8000/docs`.
The complete Prompt 3 endpoint and persistence reference is in
[`docs/api.md`](docs/api.md).

## Tests

```powershell
python -m pytest -v
python -m pytest backend/tests/test_simulator.py -v
```

The simulator scenarios `NORMAL_HOME`, `HOT_OCCUPIED_ROOM`, `EMPTY_ROOM`,
`PEAK_TARIFF`, `HIGH_ENERGY_LOAD`, `ENERGY_ANOMALY`, and `USER_OVERRIDE` are
covered by the regression suite.

## Prompt 5 ML

Train all lightweight models and write compressed artifacts to
`backend/models` (the artifacts are gitignored):

```powershell
python -m backend.training.train --samples 1500 --seed 42 --output-dir backend/models
```

Training metrics are saved in `backend/models/metrics.json`. The agent loads
valid artifacts independently. Missing, corrupt, or incompatible artifacts
automatically use the deterministic Prompt 4 baseline; predictions expose
`prediction_source` as `ML` or `BASELINE_FALLBACK`. See
[`docs/ml-architecture.md`](docs/ml-architecture.md),
[`docs/ml-training.md`](docs/ml-training.md), and
[`docs/ml-model-evaluation.md`](docs/ml-model-evaluation.md).
