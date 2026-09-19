# Prompt 4 decision algorithm

## Perception and prediction

The agent validates the current simulator state, then estimates 15-minute
natural thermal drift and cooling energy with a deterministic baseline. It
also reports a 0–100 comfort score and a simple power-deviation anomaly score.
These are transparent estimates, not ML probabilities.

## Candidates and utility

The AC candidate set is:

- `AC_OFF`
- `AC_ON_24`
- `AC_ON_25`
- `AC_ON_26`

Unsafe candidates are removed before scoring. The configurable loss is:

```text
loss = comfort_weight * comfort_penalty
     + energy_weight * tariff_cost
     + gamma * peak_load_penalty
     + delta * switching_penalty
     + preference_penalty
     + priority_penalty
```

The exposed `total_utility` is the negative loss, so the highest utility wins.
`ReasoningEngine(alpha, beta, gamma, delta, peak_limit_kw)` controls the
objective coefficients. The result exposes a deterministic loss gap, not a
calibrated probability or fabricated confidence value. `BALANCED`, `COMFORT`, and `ENERGY_SAVING`
preferences adapt comfort and energy weights.

## Override and feedback

An active appliance override prevents candidates that change the overridden
state. The chosen command is sent through the simulator, never directly
mutating a duplicate appliance model. Feedback records action success,
predicted-versus-actual temperature error, energy before/after/delta, comfort
before/after, and the selected action.

## Worked example

For 29°C, 70% humidity, two occupants, AC OFF, and a normal tariff, perception
identifies an occupied comfort risk. Prediction estimates cooling requirement
and expected energy. All four AC candidates are scored for comfort, tariff
cost, peak load, switching, preference, priority, and safety. The best valid
candidate is selected, executed through the simulator, observed after five
simulated minutes, persisted with feedback, and explained. The exact setpoint
is determined by the configured weights and current simulator state rather than
an `if temperature > 28` rule.
