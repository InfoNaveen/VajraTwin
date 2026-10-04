"""API-surface tests via FastAPI TestClient (runs in demo mode)."""

from __future__ import annotations


# ── health / docs ────────────────────────────────────────────────────────────
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "operational"
    assert "demo_mode" in body["database"]


def test_openapi_and_docs(client):
    assert client.get("/openapi.json").status_code == 200
    assert client.get("/docs").status_code == 200


def test_demo_mode_active(client):
    # conftest points MONGODB_URI at an unreachable host -> demo mode
    body = client.get("/health").json()
    assert body["database"]["demo_mode"] is True
    assert body["database"]["backend"] == "in_memory_demo"


# ── telemetry ────────────────────────────────────────────────────────────────
def test_post_telemetry(client):
    frame = {
        "engine_id": "test-eng", "rpm": 5000, "map_kpa": 105, "oat_c": 15,
        "egt_avg_c": 700, "cht_avg_c": 110, "oil_temp_c": 90,
        "oil_pressure_psi": 65, "vibration_rms_g": 1.4, "dt_s": 1.0,
    }
    r = client.post("/api/telemetry", json=frame)
    assert r.status_code == 200
    a = r.json()
    for k in ("telemetry", "twin_state", "expected", "residuals",
              "anomaly", "fault", "degradation", "rul", "advisory", "explanation"):
        assert k in a


def test_telemetry_latest_and_history(client):
    frame = {"engine_id": "hist-eng", "rpm": 4800, "map_kpa": 100, "oat_c": 15,
             "egt_avg_c": 690, "cht_avg_c": 108, "oil_temp_c": 88,
             "oil_pressure_psi": 66, "vibration_rms_g": 1.3, "dt_s": 1.0}
    client.post("/api/telemetry", json=frame)
    latest = client.get("/api/telemetry/latest?engine_id=hist-eng")
    assert latest.status_code == 200
    hist = client.get("/api/telemetry/history?engine_id=hist-eng&limit=10")
    assert hist.status_code == 200
    assert isinstance(hist.json(), list)


def test_telemetry_malformed_rejected(client):
    r = client.post("/api/telemetry", json={"rpm": "not-a-number"})
    assert r.status_code == 422  # pydantic validation


# ── engine analytics ─────────────────────────────────────────────────────────
def test_engine_endpoints(client):
    eid = "rotax-914-uav-01"
    client.post(f"/api/simulation/start?engine_id={eid}")
    for _ in range(6):
        client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5")
    assert client.get(f"/api/engine/{eid}/health").status_code == 200
    assert client.get(f"/api/engine/{eid}/diagnostics").status_code == 200
    assert client.get(f"/api/engine/{eid}/degradation").status_code == 200
    assert client.get(f"/api/engine/{eid}/rul").status_code == 200


# ── simulation control ────────────────────────────────────────────────────────
def test_simulation_lifecycle(client):
    eid = "sim-eng"
    assert client.post(f"/api/simulation/start?engine_id={eid}").json()["running"] is True
    assert client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5").json()["advanced"] is True
    assert client.post(f"/api/simulation/pause?engine_id={eid}").json()["paused"] is True
    # paused -> tick does not advance
    assert client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5").json()["advanced"] is False
    assert client.post(f"/api/simulation/resume?engine_id={eid}").json()["paused"] is False
    assert client.post(f"/api/simulation/speed?engine_id={eid}", json={"speed": 2.0}).json()["speed"] == 2.0
    assert client.post(f"/api/simulation/scenario?engine_id={eid}", json={"scenario": "HIGH_CHT", "severity": 0.8}).json()["scenario"] == "HIGH_CHT"
    assert client.get(f"/api/simulation/status?engine_id={eid}").status_code == 200
    assert client.post(f"/api/simulation/stop?engine_id={eid}").json()["running"] is False
    reset = client.post(f"/api/simulation/reset?engine_id={eid}").json()
    assert reset["scenario"] == "HEALTHY" and reset["tick"] == 0


def test_simulation_invalid_scenario(client):
    r = client.post("/api/simulation/scenario?engine_id=sim-eng", json={"scenario": "NONSENSE"})
    assert r.status_code == 400


# ── mission ──────────────────────────────────────────────────────────────────
def test_mission_analyze_and_retrieve(client):
    eid = "mission-eng"
    client.post(f"/api/simulation/start?engine_id={eid}")
    for _ in range(6):
        client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5")
    r = client.post("/api/mission/analyze", json={
        "engine_id": eid, "mission_duration_hours": 4.0, "cruise_load": 0.7,
        "max_load": 0.95, "altitude_m": 4500, "environment": "HOT",
    })
    assert r.status_code == 200
    m = r.json()
    assert "completion_probability_pct" in m and "risk_level" in m
    got = client.get(f"/api/mission/{m['mission_id']}")
    assert got.status_code == 200


def test_mission_not_found(client):
    assert client.get("/api/mission/does-not-exist").status_code == 404


# ── dashboard ────────────────────────────────────────────────────────────────
def test_dashboard_summary(client):
    eid = "dash-eng"
    client.post(f"/api/simulation/start?engine_id={eid}")
    for _ in range(5):
        client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5")
    r = client.get(f"/api/dashboard/summary?engine_id={eid}")
    assert r.status_code == 200
    assert r.json()["has_data"] is True
