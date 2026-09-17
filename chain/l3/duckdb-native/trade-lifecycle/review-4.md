# Review 4 (sketch reviewer, scoped): trade-lifecycle on duckdb-native, L3 cycle 4 (verdict: pass)

Scope: two new audits under `change-contract-4.md` (`inv.trade_ownership_pin_present`, `inv.every_received_trade_persisted`) and their manifest registration; `trade.sql` verified untouched. Evidence: check ok (8 audits); run ok, 8 at zero; two-phase ok; mutate 9 mutations, zero unprotected; simulate with the constructed trade 900001 fires exactly `inv.trade_ownership_pin_present`, one row.

Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Faithfulness: pass.** The pin audit is a four-term null test over the four pin columns and nothing else. The completeness audit builds its expected set from `raw.trade_cdc` and `raw.trade_history` only, excludes a D-touched trade entirely through a per-trade `BOOL_AND(cdc_flag IS DISTINCT FROM 'D')`, and quantifies across all batches.
2. **Null handling: pass.** `IS DISTINCT FROM` is null-safe; verified DuckDB semantics for `BOOL_AND` over mixed null flags. A history-only th_t_id stays qualifying and would fire as a missing row, which is the invariant's own review trigger. Positive finding: `trade.sql` filters outcome candidates with `cdc_flag IN ('I','U')`, which is null-unsafe; the audit is strictly stronger than the projection, as an audit should be.
3. **Both halves of "exactly one row": pass** (`HAVING COUNT <> 1` over a LEFT JOIN, with the count projected).
4. **Non-circularity and containment: pass.** The audit reads `raw.trade_history.th_t_id`, for which no handoff exists; authority is the invariant's review trigger and the anchor's report_order note, as review 9 settled.
5. **Divergence closed, join-shape independent.** With the LEFT JOINs the pin audit fires; with inner joins the completeness audit would fire instead. The two are jointly total over the two permitted shapes.
6. **Manifest: pass.** Two entries, correct ids, review_sha256 equals the selection. Group fingerprints stamped on acceptance.
7. **Policy decided in SQL: none.** Deletions, change-effective-time and batch-identity untouched by name.

Failure class: none. Rejected artifacts: none.

## Coordinator notes

- The contract's sentence "add NOT NULL to the nullable-false columns if you keep the LEFT JOIN" was wrong and the Developer rightly did not act on it: a NOT NULL would abort the MERGE on trade 900001 before any audit ran, turning a reportable violation into a load failure and deciding a disposition the model reserves. Struck from the positions contracts in flight.
- Routed to the next trade-lifecycle text cycle: `inv.every_received_trade_persisted.necessity` still carries a per-report parenthetical ("excluding cdc_flag D reports") that reads as the exclusion review 8 rejected; the statement and audit implement the whole-trade reading.
- Recorded, not actionable at L3: the completeness audit is one-directional (reported implies persisted); a governed row no source reports is caught by no deterministic audit.
