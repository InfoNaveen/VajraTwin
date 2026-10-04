# VajraTwin — API Overview

The backend is FastAPI. The **authoritative, always-current** API spec is
auto-generated:

- Interactive docs: `http://localhost:8000/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

This page is a convenience summary only; it is not duplicated spec.

## Endpoints

### Health
| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service + database (demo-mode) + AI provider status |
| GET | `/` | Service metadata |

### Telemetry
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/telemetry` | Analyse one telemetry frame (full closed-loop) |
| GET | `/api/telemetry/latest` | Latest stored frame for an engine |
| GET | `/api/telemetry/history` | Recent frames for an engine |

### Engine analytics
| Method | Path |
|---|---|
| GET | `/api/engine/{engine_id}/health` |
| GET | `/api/engine/{engine_id}/diagnostics` |
| GET | `/api/engine/{engine_id}/degradation` |
| GET | `/api/engine/{engine_id}/rul` |

### Simulation
| Method | Path |
|---|---|
| POST | `/api/simulation/start` |
| POST | `/api/simulation/stop` |
| POST | `/api/simulation/pause` |
| POST | `/api/simulation/resume` |
| POST | `/api/simulation/reset` |
| POST | `/api/simulation/scenario` |
| POST | `/api/simulation/speed` |
| POST | `/api/simulation/tick` |
| GET | `/api/simulation/status` |

### Mission
| Method | Path |
|---|---|
| POST | `/api/mission/analyze` |
| GET | `/api/mission/{mission_id}` |

### Fleet
| Method | Path |
|---|---|
| GET | `/api/fleet/summary` |
| GET | `/api/fleet/aircraft` |
| GET | `/api/fleet/{uav_id}` |
| POST | `/api/fleet/{uav_id}/scenario` |
| POST | `/api/fleet/{uav_id}/reset` |
| POST | `/api/fleet/reset` |

### Dashboard
| Method | Path |
|---|---|
| GET | `/api/dashboard/summary` |

## Error handling

- Validation errors → `422` (Pydantic).
- Unknown UAV / mission → `404` with a structured `{"detail": ...}`.
- Invalid scenario → `400`.
- Unhandled errors → `500` with a generic structured message (no stack traces
  leaked to the client); the full trace is logged server-side.
