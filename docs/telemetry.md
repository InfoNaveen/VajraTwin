# Telemetry Schema (Synthetic)

> **This is PHYSICS-COUPLED SYNTHETIC TELEMETRY** produced by the built-in
> simulator for demonstrator operation, controlled fault injection and system
> validation. It is **not** real DRDO/UAV operational telemetry.

The fields below are exactly what the simulator (`app/simulation/simulator.py`)
emits and what the physics engine consumes. No invented fields.

## Fields

| Field | Unit | Description |
|---|---|---|
| `engine_id` | — | Engine/UAV identifier |
| `timestamp` | s (epoch) | Wall-clock time of the frame |
| `sim_time_s` | s | Monotonic simulation clock (used for RUL/degradation trends) |
| `tick` | — | Monotonic frame counter |
| `rpm` | rev/min | Engine speed |
| `map_kpa` | kPa | Manifold absolute pressure |
| `oat_c` | °C | Outside air temperature |
| `egt_avg_c` | °C | Exhaust gas temperature (average) |
| `cht_avg_c` | °C | Cylinder head temperature (average) |
| `oil_temp_c` | °C | Oil temperature |
| `oil_pressure_psi` | psi | Oil pressure |
| `fuel_flow_lph` | L/h | Fuel flow |
| `vibration_rms_g` | g | Vibration RMS |
| `throttle_pct` | % | Throttle / load setting |
| `altitude_m` | m | Altitude (from mission phase) |
| `mission_phase` | — | TAXI / TAKEOFF / CLIMB / CRUISE / LOITER / DESCENT |
| `dt_s` | s | Simulation time step for this frame |
| `active_scenario` | — | Current scenario key |
| `fault_severity` | 0–1 | Active fault severity |
| `data_label` | — | Always `SYNTHETIC` |

## Physical coupling

A single latent **load demand** (set by the mission phase + a smooth random
walk) drives the primary parameters together:

```
load ↑  ⇒  RPM ↑ · MAP ↑ · EGT ↑ · CHT ↑ · oil temp ↑ · fuel flow ↑ · vibration ↑
          oil pressure ↓ (slightly, with heat/load)
```

Small Gaussian jitter is added per channel to emulate sensor noise. All values
are clamped to physically plausible ranges before emission.

## Fault scenarios

Each scenario mutates the healthy baseline by a severity-scaled signature
(`app/simulation/scenarios/definitions.py`):

| Scenario | Signature |
|---|---|
| `HEALTHY` | none |
| `HIGH_EGT` | EGT ↑, slight CHT ↑, fuel ↓ |
| `HIGH_CHT` | CHT ↑↑, oil temp ↑, oil pressure ↓ |
| `LOW_OIL_PRESSURE` | oil pressure ↓↓, oil temp ↑, vibration ↑ |
| `HIGH_VIBRATION` | vibration ↑↑, EGT ↓ (misfire), CHT ↓ |
| `TURBO_BOOST` | MAP ↑, EGT ↑, CHT ↑, fuel ↑ |
| `SENSOR_DRIFT` | EGT bias only (no corroborating change) |
| `COMBINED_FAULT` | cooling + oil + vibration simultaneously |
| `DEGRADING` | progressive multi-parameter drift over time |

## Accepted input aliases

The physics engine accepts common aliases so external/synthetic sources
interoperate: `rpm/RPM`, `map_kpa/map_pa/MAP`, `egt_avg_c/egt_c/EGT`,
`cht_avg_c/cht_c/CHT`, etc. NaN/inf values are rejected and impossible values
clamped so malformed telemetry never crashes the backend.
