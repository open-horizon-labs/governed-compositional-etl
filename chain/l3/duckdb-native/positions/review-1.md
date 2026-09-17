# Review 1 (sketch reviewer, scoped): positions on duckdb-native (verdict: fail)

Scope: cycle-1 projection under `change-contract-1.md`: `manifest.json`, `holding_change.sql`, `account_position.sql`, `customer_position.sql`, six audits. Evidence: check ok; run ok with six audits at zero; two-phase ok with positions keyed only to account 428's 2012 statement after the constructed 2017 statement became current; mutate four for four; cross-engine compare identical.

Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Read containment and L1.holdings-follow-trade: pass.** Reads exactly `raw.holding_history` and `governed.trade`; ownership copied as four columns off the trade row for `current_trade_number`; no `governed.account`, `governed.customer` or `is_current` anywhere. Two-phase shows the clause's point: the 2017 statement is current and owns nothing.
2. **The exclusion predicate: the failure.** The model authorizes dropping a holding change whose current trade's *ownership pin does not resolve* (`sg.holding-attribution` coverage claim, `sg.no-phantom-positions`, `hole.change_effective_time`). The SQL drops a change whose *trade row is absent* (INNER JOIN on `governed.trade`). Different sets. Upstream `trade.sql` LEFT JOINs both pins, so `governed.trade` holds rows with null `owning_account_effective_from`, `owning_customer_number`, `owning_customer_effective_from` by design; those rows pass the join, write nulls into four `nullable: false` frozen attributes, and create a `(428, NULL)` account position group that sums unrelated changes and passes every audit. Latent on the fixture. The converse, an `hh_t_id` with no trade row at all, is not hole-bounded: the model names it a review trigger on the attribute and on the handoff, so silently dropping it should have been a filed question.
3. **cdc_flag NULL as historical, D excluded, ordering: pass.** Matches the anchor's entity description and `report_order.applies_to`; the `(cdc_flag IS NULL) ASC` term ranks every incremental row above every historical row regardless of batch_date, which is what the anchor demands. Residual: several historical reports of one pair would tie (null cdc_dsn, same batch_date); `hole.batch_identity` territory, deserved a note.
4. **Write surface: pass.** WHEN MATCHED sets only the three mutable quantity columns; frozen and identity columns appear only in INSERT; quantity_change recomputed per the derivation. The header's argument that reading today's trade row equals the first-encounter value, because trade-lifecycle's columns are themselves frozen, is sound and stated.
5. **Audits: four faithful, two with gaps; seventh omitted but undocumented.** `inv.holding_quantity_updates_in_place` reuses the projection's selector CTE verbatim (verifies the write path, not the meaning) and leaves the invariant's second clause unchecked (a persisted pair with no surviving I/U report never surfaces). The key-match audits use the number column as the unmatched sentinel, so a `(428, NULL)` key passes the account audit silently while the customer audit fires under the wrong name. `inv.holding_change_not_constructed` (deterministic false) is correctly without an audit but the manifest does not say so.
6. **Provenance: clean.** Every selected id in exactly one place; sha matches. The exclusion's authority lives in group and hole prose, which the manifest cannot cite by element id; that is why it belonged in `questions_for_authority` or an artifact note.
7. **Policy decided in SQL: two, both on `hole.deletions` and the unknown-trade case.** A pair whose only reports are D yields no row at all, deciding row existence the hole reserves; an unknown `hh_t_id` is dropped where the model says review.

Failure class: model-stated exclusion implemented by a proxy condition that is neither necessary nor sufficient, admitting nulls into non-nullable frozen attributes and aggregate keys.

## Artifact notes

- `holding_change.sql` header lines 3-4 claim Batch1 rows are loader-normalized to I/0; the anchor and the file's own later block say the opposite. Stale text.
- `CREATE TABLE IF NOT EXISTS` declares no NOT NULL on six `nullable: false` columns; house style, but the mechanism by which finding 2 goes silent.
- The two position artifacts are clean.

## For authority (routed as L2 cycle-4 contract items)

- Unknown `hh_t_id`: drop, surface, or fail? Mechanized as a deterministic invariant so its breach fires rather than vanishes.
- Ownership presence: the exclusion rule as an invariant, so a null pin on a persisted row is a violation.
- Coverage gap: no invariant states `quantity_change = after_qty - before_qty` or `net_quantity = sum(quantity_change)`; both attributes are mutable, so the mutation harness never touches them and `unprotected: []` reads wider than it is.
- D-only pairs: L3 files the question; `hole.deletions` already reserves it.

Rejected artifacts: `holding_change.sql` (predicate, header), `audits/inv.holding_quantity_updates_in_place.sql` (second clause). Position artifacts and the other five audits stand pending the L2 change.
