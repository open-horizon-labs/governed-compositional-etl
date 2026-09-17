# Projection review 2 (scoped): trade-lifecycle on duckdb-native (verdict: pass)

Reviewer: Opus judge. History preferred where it exists per report_order; customer pin resolved off the pinned account statement's customer as of placed_at, inserted only; new placed_at audit non-vacuous (fires on the cycle-1 regression and on a later history row); reads exactly the four declared tables; two-phase pins all six frozen attributes; samples match.

Projection defect, authorized for the next L3 cycle: four audit predicates use <> where the invariant states equality, so a null escapes three-valued logic (owning_account_number, placed_at, first_seen_late null mutations unprotected). inv.trade_placement_reference_frozen already uses IS DISTINCT FROM for its other legs, so this is an inconsistency inside the artifact. The mutation finding routed to L2 at cycle 1 narrows to its L3 branch: no model change required.

Coverage limits named: customer 238's as-of statement equals its current one in the fixture, so the customer pin's as-of semantics rest on SQL inspection and the account analogue; recomputing audits share CTE logic with the model.
