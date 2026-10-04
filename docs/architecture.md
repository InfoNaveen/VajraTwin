# VajraTwin — Architecture

## Hierarchy

```
Fleet
  └─ UAV / Aircraft
       └─ Engine
            └─ Telemetry (synthetic)
                 └─ Physics Digital Twin
                      └─ Residuals (Δ = actual − expected)
                           ├─ Anomaly detection
                           ├─ Fault diagnosis (deterministic)
                           └─ Degradation / health
                                └─ RUL (trend-based)
                                     └─ Maintenance advisory
                                          └─ Mission reliability
```

## Backend layout (`backend/app`)

```
app/
  main.py                FastAPI entry (lifespan, CORS, global error handler, /health)
  core/
    config.py            Settings from env (MONGODB_URI, CORS, LLM, …)
    logging_config.py    Structured logging
  api/
    telemetry.py         POST /api/telemetry, latest, history
    engine.py            /api/engine/{id}/{health,diagnostics,degradation,rul}
    simulation.py        start/stop/pause/resume/reset/scenario/speed/status/tick
    mission.py           /api/mission/analyze, /api/mission/{id}
    dashboard.py         /api/dashboard/summary
    fleet.py             /api/fleet/*
  physics/engine.py      Rotax 914 surrogate (single source of truth)
  ml/
    anomaly.py           rolling z-score
    fault_diagnosis.py   deterministic 8-class
    degradation.py       health index + trend
    rul.py               trend-based Monte Carlo
    mission.py           series-reliability model
    advisory.py          deterministic 4-state
    ai_provider.py       deterministic + optional LLM
  simulation/
    simulator.py         physics-coupled generator + controls
    scenarios/           9 scenario definitions
  services/
    engine_service.py    per-engine orchestration (one per engine_id)
    fleet_service.py     fleet orchestration over EngineService instances
  database/
    mongo.py             Motor client + status
    memory_store.py      in-memory demo fallback
  schemas/               Pydantic request/response models
tests/                   50 tests (physics, ml, api, e2e, fleet, demo-mode)
```

## Key design decisions

- **One physics engine, one ML pipeline, one simulator** — no duplication.
- **Service registry** keyed by `engine_id` → multiple engines (and the fleet)
  reuse the same `EngineService` class; the fleet never copies engine logic.
- **Deterministic safety path** — fault class and advisory are rule-based and
  reproducible. The AI layer only explains; it never overrides state.
- **Demo-mode fallback** — MongoDB is primary, but any connection failure
  switches to an in-memory store so the app never crashes without a database.
- **Thin routes** — all business logic lives in services; routers are HTTP-only.

## Frontend layout (`frontend/src`)

```
App.tsx                  view router: Fleet ↔ Engine drill-down
services/api.ts          centralized API client (VITE_API_BASE_URL)
hooks/
  useVajraTwin.ts        single-engine polling loop + controls
  useFleet.ts            fleet summary polling
components/
  FleetOverview.tsx      fleet command-center view
  EngineDashboard.tsx    single-engine twin (Phase 6 UI, parameterised)
  HeroHealth, StatCard, DigitalTwinVisual, ResidualsChart,
  DiagnosticsPanel, DegradationPanel, RulPanel,
  SystemStatusPanel, SimulationControl, MissionSimulator, AdvisoryBadge,
  TopBar
types/index.ts           types mirroring backend responses
```

## Request lifecycle (live dashboard)

The frontend polls `POST /api/simulation/tick` (~1.5 s) while a simulation runs;
each response is a full `Analysis` object that updates every panel. `/health`
is polled (~5 s) for connection + demo-mode status. The fleet view polls
`GET /api/fleet/summary` (~2.5 s).
