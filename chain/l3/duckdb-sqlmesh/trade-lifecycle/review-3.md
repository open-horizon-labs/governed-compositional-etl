# Projection review 3 (coordinator, audit null sensitivity): trade-lifecycle on duckdb-sqlmesh (verdict: pass)

Scope: the audit-only change. Two audits changed (first-seen-late iff and the placement-reference legs with a null placed_at); the others already used IS DISTINCT FROM or compare a COUNT. Verified: check ok, run ok with six audits clean, and the mutation harness, now able to reach the physical table behind a SQLMesh view, reports seven mutations with zero unprotected. Reviewer: coordinator, on a deterministic acceptance criterion.
