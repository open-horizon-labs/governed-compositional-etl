---
id: issue-6-revalidation-cone
status: achieved
owner_hat: pipeline-platform-team
---

# Outcome

For the bounded historical Trade edge, a changed governed lifecycle field produces a semantic cone with precision 1.0 and recall 1.0 against the frozen exhaustive descendant oracle. The run includes the active case, curated regression, affected path invariants, and executable SQLMesh audits; omission of any known descendant fails.

The full-replay control also has recall 1.0 and remains the safety baseline. Its larger node count is recorded without treating reduced work as success by itself. Any future escape or routine convergence toward full replay fires issue #6's review trigger.

The pipeline-platform-team review trigger fired when independent review found that the first harness calculated cones but reused a shared already-built database. The responsible-hat decision was to fix the evidence harness and continue without changing the compositional method. The retained run now proves an isolated SQLMesh restatement of two affected models and a separate isolated full refresh of all six, with live outputs scored from each replayed database. No descendant escaped after the fix.
