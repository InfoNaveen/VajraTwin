# VajraTwin — SIH Demo Guide

A reproducible 2–4 minute demonstration of the full fleet → engine →
physics/ML → RUL → advisory → mission story.

## Prerequisites

Two terminals:

```bash
# Terminal 1 — backend
cd backend
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm run dev          # http://localhost:5173
```

(Or `docker compose up --build` and open http://localhost:8080.)

If MongoDB is not running, the TopBar shows **DEMO MODE** — this is expected and
fully functional.

## Demo sequence

1. **Open the GCS** at http://localhost:5173. The **Fleet Overview** loads.
2. **Show 6 UAVs** (UAV-001 … UAV-006) with health, status and RUL. Note the
   initial distribution (healthy + a couple needing attention) comes from the
   real diagnostic pipeline, not hardcoded numbers.
3. **Select UAV-002** → the single-engine **Digital Twin** dashboard opens.
4. Click **START** in the Simulation Control Center.
5. **Show healthy operation**: health ~85+, fault NORMAL, advisory **GO**,
   residuals near zero, twin "SYNCHRONISED".
6. In the scenario grid, click **High CHT** to inject the fault.
7. **Telemetry deviation**: CHT climbs above its expected baseline (the CHT stat
   card turns alert-red).
8. **Residual change**: the Thermal Residuals chart shows ΔCHT rising past its
   warn band.
9. **Diagnosis**: the Diagnostics panel shows the fault class (CHT_OVERHEAT or
   MULTI_PARAMETER_FAULT) with contributing parameters and an explanation.
10. **Health decline**: the Degradation panel's health index falls and trend
    reads DEGRADING.
11. **RUL change**: the Trend-based RUL estimate drops (with its honesty note).
12. **Maintenance advisory**: the hero badge escalates to **GO WITH DERATE** or
    **MAINTENANCE REQUIRED**.
13. **Mission risk**: open the Mission Reliability Simulator, click **ANALYZE
    MISSION** → completion probability drops, risk rises, limiting factor shown.
14. Click **FLEET** (top-left) to return to the Fleet Overview.
15. **UAV-002 is now the highest maintenance priority**, status CRITICAL, listed
    #1 in the maintenance-priority panel with its reason.
16. **Drill back into UAV-002** — the detailed dashboard shows the same
    underlying state (fleet view == engine view).
17. In the engine dashboard click **RESET** (or **RESET FLEET** on the overview)
    → UAV-002 returns to the deterministic healthy state.

## The demonstrator story

```
FLEET            → which UAV needs attention?
UAV SELECTION    → why does this UAV need attention?
ENGINE TWIN      → what is happening to the engine?
PHYSICS + ML     → diagnosis from residuals
RUL + ADVISORY   → what should we do?
MISSION          → can this aircraft complete the mission?
```

## Talking points (honest framing)

- "All telemetry is **physics-coupled synthetic** data from our simulator."
- "Fault diagnosis and advisory are **deterministic** — reproducible and
  auditable, not a black box."
- "RUL is a **trend-based estimate on synthetic degradation**, not a certified
  engine-life figure."
- "Anomaly score is statistical novelty; it can relax under a sustained fault.
  The **fault class, severity, health and RUL** are what drive decisions."
- "The fleet layer reuses the **same engine twin** per UAV — it scales from one
  engine to a fleet without duplicating logic."
