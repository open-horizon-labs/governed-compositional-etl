---
id: compositional-etl-experiment
outcome: governed-compositional-etl-repair
type: metric
threshold: "Pre-register after the oracle pilot: compositional CESS must improve edge/composition localization or reduce authority/regression failures versus stage-local CESS without missing affected descendants."
status: observed-revise
s_and_t_step: E5
parent_step: root
sufficiency_group: SG-PROOF
owner: research-sponsor
review_trigger: "Before the first scored comparison run, or when the oracle pilot cannot support a stable threshold."
---

Measure boundary-localization accuracy, active-case repair, unauthorized artifact changes, held-out semantic regressions, escaped composition failures, revalidation precision and recall, operator time, model usage, and compute cost.

Do not treat fewer reruns as an improvement unless every affected descendant remains covered. Do not claim success from deterministic checks without separate review of the same cases against the current Sketch.

## Valid observation

V2.4 is the sole valid run. Compositional localization was 1.0 versus 0.6 stage-local and 0.4 native; it retained zero authority violations, zero held-out regressions, and revalidation precision/recall 1.0/1.0. The frozen scorer credited one incremental composition catch and active repair 0.5, below the adoption threshold. The research-sponsor decision is `revise`.
