---
id: issue-7-matched-experiment
status: achieved-bounded
owner_hat: data-architect
---

# Matched stage, edge, and composition experiment

The valid v2.4 materialized run demonstrated that compositional evidence can locate and repair the genuine edge and path failures while native and stage-local evidence remain inconclusive. It retained independent start hashes, real wrong/right outputs, actual diffs, separate deterministic and Sketch review, sealed aggregates, localized/full replay, and a passing tamper envelope.

The frozen scorer's order-sensitive descendant comparison reduced the earned score to one incremental composition catch, so the preregistered result is `revise`, not adopt. Issue #8 owns the bounded adoption decision and must retain this inconclusive scoring limitation and all publication gates.
