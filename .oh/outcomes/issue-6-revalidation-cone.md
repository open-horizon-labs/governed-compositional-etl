---
id: issue-6-revalidation-cone
status: achieved
owner_hat: pipeline-platform-team
---

# Outcome

For the bounded historical Trade edge, a changed governed lifecycle field produces a semantic cone with precision 1.0 and recall 1.0 against the frozen exhaustive descendant oracle. The run includes the active case, curated regression, affected path invariants, and executable SQLMesh audits; omission of any known descendant fails.

The full-replay control also has recall 1.0 and remains the safety baseline. Its larger node count is recorded without treating reduced work as success by itself. Any future escape or routine convergence toward full replay fires issue #6's review trigger.
