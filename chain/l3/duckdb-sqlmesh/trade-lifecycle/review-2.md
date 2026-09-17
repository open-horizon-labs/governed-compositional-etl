# Projection review 2 (scoped): trade-lifecycle on duckdb-sqlmesh (verdict: pass)

Reviewer: Opus judge. placed_at and first_seen_late derive across both sources with existence preference for the history row, matching the invariant's wording; the cdc-only fallback branch was exercised by emptying raw.trade_history on a scratch copy and reverts to cycle-1 behavior; owning_customer_effective_from resolves the pinned account statement's customer as of placed_at and is frozen by the materialization's update set; the new placed_at audit fires on the pre-fix snapshot value and on a later history row; reads exactly the four declared tables; two-phase pins all six frozen attributes; samples match.

Named, not failed: COALESCE coalesces on value, safe while th_dts and th_st_id are anchored non-null identifiers; the recomputing audits would turn red on a late-arriving earlier report while frozen values are preserved (acknowledged model assumption; proposal filed for the business).
