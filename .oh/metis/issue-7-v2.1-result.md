---
id: issue-7-v2.1-result
status: accepted-evidence
owner_hat: data-architect
---

# V2.1 matched experiment result

The valid v2.1 run used the preregistered five-case corpus, independently copied and hash-verified databases, byte-matched starting projections, one shared deterministic repair policy, one attempt per case, zero model calls, rotated sealed custody, actual artifact edits, live SQLMesh/DuckDB execution, and actual localized/full replay evidence.

The compositional arm localized all five visible cases, repaired all four authority-resolved cases, preserved the missing-policy case as inconclusive, caught both composition cases, produced zero authority violations and zero held-out regressions, and retained semantic revalidation precision and recall of 1.0. Native and stage-local arms each caught zero of the two composition cases; their local producer and consumer checks still passed for the governed edge case. Compositional work was 24 deterministic work units versus 19 native units (1.263x), below the preregistered 4x ceiling. Wall time is descriptive only.

The preregistered threshold evaluation yields `adopt` for this bounded scripted slice. This is evidence for issue #8's research-sponsor decision, not a general correctness, production-readiness, compliant TPC-DI benchmark, or performance claim. The issue #7 edge-reduces-to-local review trigger did not fire. V1 and v2 attempt A remain invalid and contribute nothing.
