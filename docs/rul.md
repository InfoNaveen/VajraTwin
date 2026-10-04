# Trend-based RUL Estimator — Methodology & Honesty

## What it is

VajraTwin's Remaining Useful Life (RUL) output is a **trend-based estimator**
operating on the synthetic digital-twin health signal
(`app/ml/rul.py`).

## What it is NOT

It is **not**:
- a certified engine-life prediction
- a validated operational lifetime
- a guaranteed remaining engine-hours figure
- trained/validated against real run-to-failure data

The UI and API responses carry this note:

> *"Based on synthetic degradation data; demonstrator estimate — not a certified
> flight-safety prediction."*

## Method (high level)

1. The degradation engine produces a smoothed `health_index` (0–100) each frame.
2. The RUL estimator keeps a short history of `(sim_time, health)` samples.
3. It fits a least-squares slope → observed degradation rate (health per minute).
4. If the trend is flat/improving → status `STABLE_NO_DECAY` (no finite RUL).
5. If history is too short → status `INSUFFICIENT_HISTORY` (returns a clear
   message rather than inventing a number).
6. Otherwise it projects time until the health reaches the failure band and maps
   simulated time to flight-hours via a **documented synthetic scaling constant**
   (`_SIM_MIN_TO_FLIGHT_HOURS`). A 300-path Monte Carlo perturbation of the decay
   rate yields a P5–P95 confidence interval.

## Output fields

| Field | Meaning |
|---|---|
| `status` | `OK` / `INSUFFICIENT_HISTORY` / `STABLE_NO_DECAY` |
| `rul_hours` | Point estimate (flight hours) or `null` |
| `confidence_interval` | `[P5, P95]` hours or `null` |
| `degradation_trend_per_min` | Observed health loss per simulated minute |
| `methodology` | Human-readable method string |

## Why this is honest

The failure threshold, decay model and time-scaling are all explicit and
documented in code. There is no claim of real-world validity. The estimate is a
transparent engineering projection suitable for a demonstrator.
