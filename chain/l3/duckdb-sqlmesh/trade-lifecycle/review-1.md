# Projection review 1: trade-lifecycle on duckdb-sqlmesh (verdict: pass, unconditional)

Reviewer: Opus judge with the L2 model as Sketch; ran check, run, twophase; perturbed a scratch copy to confirm each of the five audits is live.

Holds: materialization properties list exactly the six mutable and five frozen attributes; physical types match; selectors as named; no is_current, no effective_to; first report by report_order without a flag filter; D excluded only in latest_change; two-phase result identical to the native target.

Named, not failed: the final joins silently omit a trade whose pin does not resolve or that has no I or U report (entailed by non-nullability but not stated); inv.trade_placement_reference_frozen recomputes the pin against the current account statements, so a late-arriving account statement effective before placed_at but after the pinned one would turn the audit red while the frozen values are correctly preserved (question filed); first_seen_late has no runtime expression of its out-of-domain review trigger.

Possible model and anchor gap (filed): the per-status trade history file is not anchored, so a historical-load trade's first held report is the snapshot row with its final status; trade 353232 is placed at a completion-time t_dts and marked first seen late for that reason alone, and its ownership pin resolves as of that later moment (harmless in the fixture, not in general).
