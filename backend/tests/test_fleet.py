"""
Fleet regression test.
6 UAVs -> inject HIGH_CHT into UAV-002 -> verify aircraft + fleet aggregation +
maintenance priority change, UAV-001 unchanged, fleet state == engine state,
then reset restores deterministic state.
"""

from __future__ import annotations


def test_fleet_summary_has_six(client):
    s = client.get("/api/fleet/summary").json()
    assert s["total_aircraft"] == 6
    assert set(s["status_counts"]) == {"healthy", "attention", "critical"}
    assert len(s["aircraft"]) == 6


def test_fleet_aircraft_list(client):
    lst = client.get("/api/fleet/aircraft").json()
    assert isinstance(lst, list) and len(lst) == 6
    for ac in lst:
        assert {"uav_id", "status", "health_index", "fault_class", "advisory_state"} <= set(ac)


def test_fleet_detail_not_found(client):
    assert client.get("/api/fleet/UAV-999").status_code == 404


def test_fleet_fault_propagation_and_reset(client):
    # baseline
    before = client.get("/api/fleet/UAV-002").json()
    assert before["analysis"] is not None
    uav1_before = client.get("/api/fleet/UAV-001").json()["health_index"]
    health_before = before["health_index"]

    # inject HIGH_CHT into UAV-002 and drive its own engine
    client.post("/api/fleet/UAV-002/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    for _ in range(16):
        client.post("/api/simulation/tick?engine_id=UAV-002&dt=1.5")

    after = client.get("/api/fleet/UAV-002").json()
    assert after["health_index"] < health_before, "UAV-002 health decreased"
    assert after["fault_class"] != "NORMAL", "UAV-002 fault detected"
    assert after["advisory_state"] != "GO", "UAV-002 advisory escalated"

    # fleet aggregation reflects the change
    summary = client.get("/api/fleet/summary").json()
    assert summary["highest_risk"] is not None
    priority_ids = [p["uav_id"] for p in summary["maintenance_priority"]]
    assert "UAV-002" in priority_ids, "UAV-002 appears in maintenance priority"

    # isolation: UAV-001 roughly unchanged
    uav1_after = client.get("/api/fleet/UAV-001").json()["health_index"]
    assert abs(uav1_after - uav1_before) < 20

    # fleet view == engine view
    eng = client.get("/api/engine/UAV-002/health").json()
    assert abs(eng["health_index"] - after["health_index"]) < 0.5
    assert eng["fault_class"] == after["fault_class"]

    # reset the aircraft -> deterministic healthy state
    reset = client.post("/api/fleet/UAV-002/reset").json()
    assert reset["fault_class"] == "NORMAL"
    assert reset["status"] == "HEALTHY"


def test_fleet_reset_all_deterministic(client):
    s = client.post("/api/fleet/reset").json()
    assert s["total_aircraft"] == 6
    assert s["status_counts"]["critical"] == 0
