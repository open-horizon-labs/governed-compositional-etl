---
id: issue-7-v2.4-result
status: accepted-evidence
owner_hat: data-architect
---

# Valid v2.4 result: revise

V2.4 is the first run whose unchanged independent envelope verifier passes while proving materially observed injected and repaired outputs. In every arm, the edge defect materialized creation at `00:02:34` and the path defect materialized duration `0`. The compositional arm alone used governed contract/path evidence and repaired those values to `00:01:13` and `81`; native and stage-local remained inconclusive and retained the wrong values. Producer and consumer local checks passed in every edge case.

The arm-neutral frozen scorer counted one incremental composition catch. It rejected the otherwise correct edge and verification-gap proposals because their governance-derived descendant lists contained the exact expected members in canonical sorted order rather than the corpus's different list order. This observed mismatch is not tuned after the run. Consequently compositional active repair is 0.5, one composition failure is scored escaped, and the preregistered quality threshold fails. The valid decision is `revise`.

Compositional retained zero authority violations, zero held-out regressions, semantic revalidation precision/recall 1.0, 24 work units versus 19 native units (1.263x), and zero model usage. V1, v2 attempt A, v2.1, and v2.3 are invalid; v2.2 was rejected before scoring. Publication remains human-gated and bounded to this scripted batch slice.
