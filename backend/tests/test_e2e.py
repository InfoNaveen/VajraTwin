"""
Critical end-to-end demonstrator test (single engine).
START -> healthy -> inject HIGH_CHT -> verify full propagation chain -> reset.
"""

from __future__ import annotations


def _drive(client, eid, n, dt=1.5):
    last = None
    for _ in range(n):
        last = client.post(f"/api/simulation/tick?engine_id={eid}&dt={dt}").json()
    return last


def test_full_chain_and_reset(client):
    eid = "e2e-eng"

    # START
    assert client.post(f"/api/simulation/start?engine_id={eid}").json()["running"] is True

    # HEALTHY
    healthy = _drive(client, eid, 12)
    a = healthy["analysis"]
    assert a is not None
    assert a["fault"]["fault_class"] == "NORMAL"
    assert a["advisory"]["state"] == "GO"
    health_healthy = a["degradation"]["health_index"]
    assert health_healthy > 70

    # chain present on healthy frame
    assert "delta_cht_c" in a["residuals"]
    assert "anomaly_score" in a["anomaly"]
    assert "health_index" in a["degradation"]
    assert "status" in a["rul"]

    # INJECT HIGH_CHT
    client.post(f"/api/simulation/scenario?engine_id={eid}", json={"scenario": "HIGH_CHT", "severity": 0.9})
    faulted = _drive(client, eid, 18)
    af = faulted["analysis"]

    # verify propagation
    assert af["fault"]["fault_class"] != "NORMAL", "fault diagnosed"
    assert af["degradation"]["health_index"] < health_healthy, "health decreased"
    assert af["advisory"]["state"] != "GO", "advisory escalated"
    assert len(af["explanation"]["explanation"]) > 20, "XAI explanation present"

    # mission risk changes under fault
    m = client.post("/api/mission/analyze", json={
        "engine_id": eid, "mission_duration_hours": 4.0, "cruise_load": 0.7,
        "max_load": 0.95, "altitude_m": 4500, "environment": "HOT",
    }).json()
    assert m["risk_level"] in ("ELEVATED", "HIGH", "MODERATE")

    # RESET -> healthy state returns
    reset = client.post(f"/api/simulation/reset?engine_id={eid}").json()
    assert reset["scenario"] == "HEALTHY"
    assert reset["tick"] == 0
    # re-drive briefly and confirm it recovers to NORMAL/GO
    client.post(f"/api/simulation/start?engine_id={eid}")
    recov = _drive(client, eid, 12)["analysis"]
    assert recov["fault"]["fault_class"] == "NORMAL"
    assert recov["advisory"]["state"] == "GO"
