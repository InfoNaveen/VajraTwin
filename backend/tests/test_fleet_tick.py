"""
Fleet-OWNED progression regression tests.

These close the gap the original suite left open: the fleet must advance its six
engines *through its own tick endpoint* (POST /api/fleet/tick), not only via the
per-engine simulation endpoint. Also verifies instance identity, isolation,
state equality (fleet == engine), fleet-health = mean, and deterministic reset.
"""

from __future__ import annotations


def _ac(summary, uid):
    return next(a for a in summary["aircraft"] if a["uav_id"] == uid)


def _fleet_tick(client, n=1, dt=1.5):
    last = None
    for _ in range(n):
        last = client.post(f"/api/fleet/tick?dt={dt}").json()
    return last


# A. Fleet initialises six aircraft
def test_fleet_initialises_six(client):
    client.post("/api/fleet/reset")
    s = client.get("/api/fleet/summary").json()
    assert s["total_aircraft"] == 6
    assert len(s["aircraft"]) == 6


# B + C. Fleet tick advances all six engines and changes simulation time
def test_fleet_tick_advances_all_engines(client):
    client.post("/api/fleet/reset")
    before = client.get("/api/fleet/summary").json()
    t_before = {a["uav_id"]: a["last_update_s"] for a in before["aircraft"]}

    after = _fleet_tick(client, n=1)
    t_after = {a["uav_id"]: a["last_update_s"] for a in after["aircraft"]}

    for uid in t_before:
        assert t_after[uid] > t_before[uid], f"{uid} sim time did not advance"


# GET summary must remain read-only (does NOT advance)
def test_get_summary_is_read_only(client):
    client.post("/api/fleet/reset")
    a = client.get("/api/fleet/summary").json()
    b = client.get("/api/fleet/summary").json()
    ta = {x["uav_id"]: x["last_update_s"] for x in a["aircraft"]}
    tb = {x["uav_id"]: x["last_update_s"] for x in b["aircraft"]}
    assert ta == tb, "GET /summary must not advance simulation"


# D. Fleet tick does NOT create new EngineService instances
def test_fleet_tick_does_not_create_new_instances(client):
    from app.services.engine_service import _SERVICES
    from app.services.fleet_service import get_fleet_service

    # ensure fleet exists
    client.get("/api/fleet/summary")
    before_ids = {k: id(v) for k, v in _SERVICES.items()}
    _fleet_tick(client, n=3)
    after_ids = {k: id(v) for k, v in _SERVICES.items()}

    # the six fleet engines must be the SAME objects after ticking
    fleet = get_fleet_service()
    for uid in fleet.aircraft:
        assert uid in before_ids and uid in after_ids
        assert before_ids[uid] == after_ids[uid], f"{uid} EngineService was replaced"


# E. Fleet state equals engine state for the same UAV
def test_fleet_state_equals_engine_state(client):
    client.post("/api/fleet/reset")
    _fleet_tick(client, n=4)
    fleet_u2 = _ac(client.get("/api/fleet/summary").json(), "UAV-002")
    eng = client.get("/api/engine/UAV-002/health").json()
    assert abs(fleet_u2["health_index"] - eng["health_index"]) < 0.01
    assert fleet_u2["fault_class"] == eng["fault_class"]
    assert fleet_u2["advisory_state"] == eng["advisory"]["state"]


# F + G + H. HIGH_CHT propagates via fleet tick; fleet health + priority change
def test_high_cht_propagates_via_fleet_tick(client):
    client.post("/api/fleet/reset")
    base = client.get("/api/fleet/summary").json()
    fh_base = base["fleet_health"]
    u2_base = _ac(base, "UAV-002")["health_index"]

    client.post("/api/fleet/UAV-002/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    last = _fleet_tick(client, n=18)

    u2 = _ac(last, "UAV-002")
    assert u2["health_index"] < u2_base, "health decreased"
    assert u2["fault_class"] != "NORMAL", "fault detected"
    assert u2["advisory_state"] != "GO", "advisory escalated"
    assert u2["status"] == "CRITICAL"

    # fleet health fell
    assert last["fleet_health"] < fh_base
    # highest risk is UAV-002
    assert last["highest_risk"]["uav_id"] == "UAV-002"
    # maintenance priority lists UAV-002
    assert "UAV-002" in [p["uav_id"] for p in last["maintenance_priority"]]


# I. Maintenance priority ranks the degraded aircraft first
def test_degraded_aircraft_becomes_highest_priority(client):
    client.post("/api/fleet/reset")
    client.post("/api/fleet/UAV-002/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    last = _fleet_tick(client, n=18)
    assert last["maintenance_priority"][0]["uav_id"] == "UAV-002"


# K + L. Single aircraft reset restores deterministic healthy state
def test_single_aircraft_reset(client):
    client.post("/api/fleet/UAV-002/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    _fleet_tick(client, n=10)
    r = client.post("/api/fleet/UAV-002/reset").json()
    assert r["fault_class"] == "NORMAL"
    assert r["status"] == "HEALTHY"


# M + N. Isolation: faulting UAV-002 does not affect UAV-001
def test_uav_isolation(client):
    client.post("/api/fleet/reset")
    base = client.get("/api/fleet/summary").json()
    u1_base = _ac(base, "UAV-001")["health_index"]

    client.post("/api/fleet/UAV-002/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    last = _fleet_tick(client, n=18)

    u1 = _ac(last, "UAV-001")
    assert u1["fault_class"] == "NORMAL", "UAV-001 must stay NORMAL"
    assert abs(u1["health_index"] - u1_base) < 25


# Fleet health == unweighted mean of engine health indices
def test_fleet_health_is_mean(client):
    client.post("/api/fleet/reset")
    last = _fleet_tick(client, n=6)
    healths = [a["health_index"] for a in last["aircraft"]]
    mean = round(sum(healths) / len(healths), 1)
    assert abs(mean - last["fleet_health"]) < 0.05


# O. Full fleet reset -> deterministic distribution reproduced via real pipeline
def test_full_fleet_reset_deterministic(client):
    s1 = client.post("/api/fleet/reset").json()
    # record statuses by uav
    st1 = {a["uav_id"]: a["status"] for a in s1["aircraft"]}
    # perturb then reset again
    client.post("/api/fleet/UAV-004/scenario", json={"scenario": "HIGH_CHT", "severity": 0.9})
    _fleet_tick(client, n=8)
    s2 = client.post("/api/fleet/reset").json()
    st2 = {a["uav_id"]: a["status"] for a in s2["aircraft"]}
    assert s2["status_counts"]["critical"] == 0
    assert st1 == st2, "fleet reset must reproduce the same deterministic distribution"


# P. tick endpoint returns the full fleet summary schema
def test_fleet_tick_returns_summary_schema(client):
    s = client.post("/api/fleet/tick?dt=1.5").json()
    for key in (
        "total_aircraft", "status_counts", "fleet_health",
        "highest_risk", "maintenance_priority", "fault_distribution", "aircraft",
    ):
        assert key in s
