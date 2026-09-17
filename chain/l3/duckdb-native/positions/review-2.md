# Review 2 (sketch reviewer, scoped): positions on duckdb-native, L3 cycle 2 (verdict: fail, narrow)

Scope: the cycle-2 change under `change-contract-2.md`: predicate and header of `holding_change.sql`, the extended `inv.holding_quantity_updates_in_place` audit, six new audits, manifest provenance, artifact note and one filed question. Evidence: check status question, zero problems, 12 audits; run ok, 12 at zero; two-phase ok; mutate 14, zero unprotected; cross-engine compare identical.

Reviewer: Opus sketch reviewer, seven scope questions.

## Rejected artifact

`manifest.json`, artifact note only: it claims the duckdb-sqlmesh sibling "carries an audit stub" for `inv.holding_change_not_constructed` and that this target omits one by design. No such file exists; the sibling carries a note saying the invariant has no SQL audit. A false cross-target claim in the provenance record, seeded by the contract's ambiguous parenthetical ("the sqlmesh sibling has one", meaning the note). One-sentence fix.

## Findings

1. **Exclusion predicate: the cycle-1 failure is repaired.** LEFT JOIN on `governed.trade` and keep only when all four copied values are non-null; both a missing trade row and a null-pin trade row are excluded, which is the model's rule. Header precise about which three columns can be null on this engine. Read containment unchanged.
2. **Six new audits: faithful, non-circular, null-sensitive.** current_trade_known quantifies over reports with `IS DISTINCT FROM 'D'`; ownership_present checks four columns, quantities_present three; the sum audits check value equality and both directions of key existence with null-safe joins.
3. **updates_in_place: independence is real.** Latest report restated as "a report nothing dominates" via correlated NOT EXISTS; the dominance relation partitions persisted rows exactly into stale and orphaned; tie accommodation attributed to hole.batch_identity.
4. **Write surface unchanged.**
5. **Manifest: provenance and question correct**; all 52 selected ids covered; the note is the rejection.
6. **Header: pass**; the NOT NULL reasoning accurate.
7. **Policy decided in SQL: nothing beyond the filed question.** Residual tension recorded: the orphaned clause enforces one answer to the filed question (a persisted D-only pair must not exist).

Failure class: unverified cross-target claim asserted as fact in the provenance record.

## Recorded

- Sum audits check key existence, not cardinality; duplicates are structurally impossible under the GROUP BY rebuild.
- D-scoping differs in phrasing between audits (`IS DISTINCT FROM 'D'` versus `IS NULL OR IN ('I','U')`), mirroring the model's two wordings.
- Converse gap: no invariant says an eligible report whose trade fully resolves yields a holding_change row.

## CE proposals (the first routed as positions cycle 6)

1. Extend `ce.l2.trade-before-account-statement` with a holding report naming trade 900001. On native the trade persists with null pins, the new predicate excludes the report and no positions audit fires; on SQLMesh the trade has no row and `inv.holding_change_current_trade_known` fires. Same L2 invariant, engine-dependent outcome, driven by the upstream join shape. The invariant's "resolves to a logical.trade row" should read "resolves to a fully pinned logical.trade row" so the case fires on every engine.
2. A tie counterexample for hole.batch_identity (two historical reports of one pair, same batch_date, null cdc_dsn, different quantities).
3. A pin-resolves-partially case (account statement resolves, customer statement does not): the change drops out of both sums with every audit at zero; model-authorized silence that nothing demonstrates.

Rejected artifacts: `manifest.json` (note sentence).
