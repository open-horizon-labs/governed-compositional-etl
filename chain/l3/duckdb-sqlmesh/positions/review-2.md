# Review 2 (sketch reviewer, scoped): positions on duckdb-sqlmesh, L3 cycle 2 (verdict: fail, narrow)

Scope: the cycle-2 change under `change-contract-2.md`: the two not-negative audits, the extended `inv.holding_quantity_updates_in_place`, six new AUDIT files, the three models' audits lists (SELECT bodies verified unchanged), manifest provenance and one filed question. Evidence: check status question, zero problems, 12 audits; run ok, 12 at zero; two-phase ok; mutate 14, zero unprotected; cross-engine compare identical.

Reviewer: Opus sketch reviewer, seven scope questions.

## Rejected artifact

`audits/inv.holding_quantity_updates_in_place.sql`. Clause 2 is covered and the latest-report selection is restated independently (correlated NOT EXISTS), but when several reports of one pair tie under report_order (the hole.batch_identity case the comment names) the anti-join yields every tied candidate, the final LEFT JOIN fans out, and a persisted row that adopted one tied candidate is reported as a violation; on this engine a blocking audit then refuses the plan. The comment says the job does not resolve the tie; the SQL resolves it in the strict direction. The native sibling resolves it the other way (any undominated candidate matching passes). Same L2, two audit semantics, invisible to compare because the fixture has no tie. Also: the candidate filter is `IS DISTINCT FROM 'D'` while the model's own selector is `IS NULL OR IN ('I','U')`; they agree only over the anchored vocabulary. Remedy: the tolerant form (a violation only when no undominated candidate matches), the model's filter, and a true comment; or the strict form with a second filed question.

## Findings

1. **Not-negative audits: pass**, null-sensitive; models changed only in their audits lists; materialization properties untouched.
2. **Six new audits: five faithful, one partial.** ownership_present four columns; quantities_present three; the difference audit and quantities_present are jointly complete on nulls; current_trade_known quantifies over raw reports with `IS DISTINCT FROM 'D'` and correctly carries no `@this_model`. The sum audits check value equality and both directions of key existence but not the "exactly one" cardinality half; unreachable under the GROUP BY rebuild, so not rejected.
3. **updates_in_place**: the rejection above.
4. **Read containment: pass.** 5. **Manifest: pass**; the filed question tracks hole.deletions' own new sentence. 6. **Comments**: one overclaim (the tie). 7. **Policy decided in SQL**: the tie strictness, beyond the filed question.

Failure class: audit semantics deciding a deferred hole in SQL, in the opposite direction from the sibling engine, against its own comment.

## Recorded

- On this engine `inv.holding_change_current_trade_known` fires for both cases the L2 distinguishes (missing trade row, unresolved pin), because the upstream model publishes no row for an unpinnable trade; the native engine excludes the report silently. The engines differ only in a state trade-lifecycle's own invariants already report; routed to positions cycle 6 as text that says so, plus the converse invariant the native review asked for.
- Sum audits join with `=` where native uses `IS NOT DISTINCT FROM`; stricter here.

## CE proposal (filed as a runnable document)

`ce.l3.holding-historical-report-tie`: two Batch1 historical reports of one pair with different after quantities, both with null cdc_flag and cdc_dsn, same batch_date. Expected before the fix: native runs clean; SQLMesh's updates_in_place audit refuses the plan. After the tolerant fix: both engines accept either candidate, and the residual is visible rather than inferred from a comment.

Rejected artifacts: `audits/inv.holding_quantity_updates_in_place.sql`. Fix folded into L3 cycle 3 with the cycle-6 audits.
