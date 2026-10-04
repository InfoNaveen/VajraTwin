"""
Demo-mode (MongoDB unavailable) hard requirement test.
The whole app must function with no MongoDB: health, simulation, engine
analysis, fleet, and mission must all work and never raise an unhandled
MongoDB exception.
"""

from __future__ import annotations


def test_backend_starts_in_demo_mode(client):
    body = client.get("/health").json()
    assert body["database"]["demo_mode"] is True


def test_simulation_works_without_mongo(client):
    eid = "demo-eng"
    client.post(f"/api/simulation/start?engine_id={eid}")
    r = client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5")
    assert r.status_code == 200
    assert r.json()["analysis"] is not None


def test_engine_analysis_works_without_mongo(client):
    eid = "demo-eng"
    assert client.get(f"/api/engine/{eid}/health").status_code == 200


def test_fleet_works_without_mongo(client):
    assert client.get("/api/fleet/summary").status_code == 200


def test_mission_works_without_mongo(client):
    eid = "demo-eng2"
    client.post(f"/api/simulation/start?engine_id={eid}")
    for _ in range(5):
        client.post(f"/api/simulation/tick?engine_id={eid}&dt=1.5")
    r = client.post("/api/mission/analyze", json={
        "engine_id": eid, "mission_duration_hours": 3.0, "cruise_load": 0.6,
        "max_load": 0.85, "altitude_m": 3000, "environment": "STANDARD",
    })
    assert r.status_code == 200


def test_telemetry_persist_does_not_crash_without_mongo(client):
    # insert path must swallow DB errors in demo mode
    frame = {"engine_id": "demo-eng3", "rpm": 5000, "map_kpa": 105, "oat_c": 15,
             "egt_avg_c": 700, "cht_avg_c": 110, "oil_temp_c": 90,
             "oil_pressure_psi": 65, "vibration_rms_g": 1.4, "dt_s": 1.0}
    assert client.post("/api/telemetry", json=frame).status_code == 200
