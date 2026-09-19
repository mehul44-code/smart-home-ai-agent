# Competition dashboard demo

1. Start the API with `python -m uvicorn backend.app.main:app --reload`.
2. Start the UI with `cd frontend; npm run dev`.
3. Use **Normal home** to establish a baseline.
4. Choose **Hot room**, then **Run agent step**. Point out perception,
   prediction source, candidates, selected action, and feedback.
5. Choose **Peak tariff** and run another step to show cost-aware reasoning.
6. Choose **Empty room** to demonstrate comfort-aware curtailment.
7. Choose **Energy anomaly** and inspect Alerts & anomalies.
8. Choose **User override**, or set an appliance to ON/OFF. Return it to AUTO
   to let the agent control it again.
9. Choose **Peak tariff laundry** and run a step. The appliance recommendation
   card shows the selected laundry action, target off-peak rate, delay, and
   that no false run was reported.
10. Choose **High-load water heater** and run a step to show the water-heater
    load/peak recommendation and override status.

The live indicator should read **connected**. If the API is unavailable, the
page keeps its layout and shows an actionable error rather than fake telemetry.
