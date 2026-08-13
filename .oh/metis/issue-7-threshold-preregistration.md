---
id: issue-7-threshold-preregistration
status: invalidated
owner_hat: research-sponsor
---

# Invalid v1 threshold preregistration

The research-sponsor hat froze `experiments/preregistration-v1.json` before the invalid v1 run. Its pseudo-millisecond and replay-wall criteria are preserved only as failed-harness history and do not govern v2.4.

V1 mislabeled deterministic work units as fabricated milliseconds. After invalidation and before the valid run, commit `e9aa5bb` froze the governing v2.4 criteria: an honest work-unit ceiling of 4.0 and measured wall time as descriptive only. The quality thresholds remain independently demanding, and v2.4 fails them.

The valid result is not rescored. External publication remains subject to human review and the TPC-DI naming and fair-use gates.
