# Smart Home AI Agent

This repository contains the Prompt 2 smart-home simulator and the Prompt 3
database/API integration. Prompt 3 stores history and user-supplied records;
the simulator remains the source of truth for current state. Autonomous agent
decision-making, ML, and the dashboard are intentionally not enabled here.

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
