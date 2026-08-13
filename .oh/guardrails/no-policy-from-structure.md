---
id: no-policy-from-structure
severity: hard
statement: "Raw data, source schemas, and target schemas may constrain structure but do not authorize missing business policy."
outcome: governed-compositional-etl-repair
---

When a transformation rule is not established by the current Sketch or an approved active counterexample, preserve it as an explicit hole. A generated mapping may be proposed for review but must not silently become policy because it is plausible or because it makes the target schema populate successfully.
