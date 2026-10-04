# Anomaly vs Fault vs Severity vs Health

VajraTwin keeps four distinct concepts separate on purpose. Conflating them is a
common dashboard mistake; here each has one clear job.

| Concept | Source | Range | Meaning |
|---|---|---|---|
| **Anomaly score** | `app/ml/anomaly.py` | 0–100 | **Statistical novelty** of the residual vector (rolling z-score) |
| **Fault classification** | `app/ml/fault_diagnosis.py` | 8 classes | **Diagnosed fault** from deterministic engineering rules |
| **Fault severity** | `app/ml/fault_diagnosis.py` | 0–1 | **Severity** of the diagnosed condition |
| **Health index** | `app/ml/degradation.py` | 0–100 | **Overall engine condition** over time |

## Important behaviour: anomaly adapts

The anomaly detector is a **rolling statistical** detector. When a fault is
present and sustained, the residual becomes the new local "normal", so the
anomaly score **relaxes over time** after the initial onset spike.

**This is expected and acceptable.** We do **not** artificially force the
anomaly score to stay high.

## What drives decisions

Decisions (advisory state, maintenance priority, mission risk) are driven by the
**deterministic** signals:

```
fault_class · fault_severity · health_index · RUL
```

not by the raw anomaly score. The anomaly score is a useful early-onset novelty
indicator and a contributor to the health index, but it is never the sole basis
for a safety decision.

## Fleet prioritisation

The fleet maintenance-priority ranking sorts by **status → health → RUL →
severity**, deliberately *not* by anomaly score, for exactly this reason.
