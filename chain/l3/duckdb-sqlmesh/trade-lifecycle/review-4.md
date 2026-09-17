# Review 4 (sketch reviewer, scoped): trade-lifecycle on duckdb-sqlmesh, L3 cycle 4 (verdict: fail, narrow)

Scope: two new AUDIT files under `change-contract-4.md` (`inv.trade_ownership_pin_present`, `inv.every_received_trade_persisted`), their registration in `manifest.json` and in the model's audits list; `models/trade.sql` verified changed only in that list. Evidence: check ok (8 audits); run ok, 8 at zero; two-phase ok; mutate 9, zero unprotected; simulate with the constructed trade 900001 fires exactly `inv.every_received_trade_persisted`, one row, as a blocking audit that refuses the plan.

Reviewer: Opus sketch reviewer, seven scope questions.

## Rejected artifact

`audits/inv.every_received_trade_persisted.sql`, final UNION branch: `row_count > 1` is evaluated over the whole model rather than over the in-scope (no D report) trade_numbers, so a D-touched trade persisted twice would be named by an invariant whose statement, parallel_assumption and `sg.trade-identity.gap` all leave such a trade to L1.hole.deletions. The native sibling scopes both halves to the qualifying set. The two engines therefore disagree in that corner, in the cycle meant to remove a disagreement. Unreachable on the fixture and by simulate (the merge's unique_key and the model's QUALIFY guarantee one row per trade), which is why mutate showed nothing; the branch exists exactly for the shape in which it would be wrong. One-line fix.

## Other findings

1. **Pin audit: exact restatement.** Completeness audit gets the hard parts right: union of both received sources; universal per-trade D test (`BOOL_AND(cdc_flag IS DISTINCT FROM 'D')`) that excludes a D-touched trade entirely, the correction review 8 demanded.
2. **Null handling: pass.** Comment inaccuracy: it justifies the null-safe form by "a historical row with a null flag", which the anchor's historical_load rules out for raw.trade_cdc; inherited from the contract's wording.
3. **Both halves present**, one mis-scoped (above).
4. **Non-circularity and containment: pass, tighter than required.** The expected set does not re-derive the pin, so it cannot be satisfied by the same inner joins that drop the trade.
5. **Divergence closed, join-shape independent.** Under inner joins the completeness audit fires; under LEFT JOINs the pin audit would fire instead. The Developer rightly did not take the contract's NOT NULL offer.
6. **Manifest and header: pass.** `depends_on` correctly untouched; group fingerprints are stamped on acceptance.
7. **Policy decided in SQL: one**, the mis-scoped branch (a deletions question). Neither audit orders by batch or history time, so batch-identity is untouched.

Failure class: over-reach into a reserved hole by one half of one audit, reintroducing a cross-engine divergence in a corner.

Rejected artifacts: `audits/inv.every_received_trade_persisted.sql`. Fix prescribed; comment correction requested.
