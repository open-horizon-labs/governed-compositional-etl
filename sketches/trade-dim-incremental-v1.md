---
id: trade-dim-incremental-v1
status: incomplete
owner_hat: data-product-owner
authority: issue-8-incremental-key-binding-adjudication (assumed; TPC-DI-1.1.0 locator unverified)
extends: trade-dim-v1
chain_position: 3
depends_on: dim-account-scd2-v1
---

# Incremental trade dimension Sketch v1

This is the human-reviewable governing Sketch for incremental Trade CDC updates into DimTrade. It is intentionally incomplete. It extends `trade-dim-v1`, whose historical rules and holes remain in force. A raw CDC row, a target column, a generated MERGE, or a materialized table may expose a hole but cannot fill it.

## Grain and identity

- `stage.trade_cdc`: one change record per `(T_ID, CDC_DSN)` within one incremental batch.
- `logical.dim_trade_incremental`: one warehouse row per `trade_id` across historical and incremental batches. `trade_id` is the natural identity; a later CDC row for the same identity is a lifecycle update, not a new row.

## Known rules in order

1. **Anchor CDC structure only.** Parse the incremental Trade file by its declared fields, including `CDC_FLAG` and `CDC_DSN`. This authorizes no classification or default.
2. **Match on natural identity.** A CDC row matches an existing DimTrade row by `trade_id`. Authority: TPC-DI 1.1.0 clause 4.5.8.1 identity, carried forward.
3. **Resolve dimension versions at first encounter only.** When a `trade_id` is not yet present, resolve `sk_account_id` and `sk_customer_id` from the account version effective as of the row's `T_DTS`. `T_DTS` is used only to look up versions, never relabeled as creation time. Authority: `issue-8-incremental-key-binding-adjudication` (assumed).
4. **Mutation roles govern the update surface.** Every semantic type carries a `mutation_role`. `identity` matches; `frozen_from_first_encounter` is written on insert only; `mutable` is written on insert and on match; `none` is never projected. Roles live on semantic types, never on column names. Authority: same decision, data-architect hat.
5. **Emit the incremental write as a MERGE whose matched-update set is exactly the mutable-role columns.** The compiler derives the `WHEN MATCHED THEN UPDATE SET` list from roles. A frozen-role column cannot appear there. A matched `DELETE` paired with a `NOT MATCHED INSERT` is a rebind by other means and is equally forbidden.
6. **Verify twice, mechanically then at run time.** The AST guard inspects any candidate projection, compiler-built or hand-written, and reports every attempted write to a frozen-role column with its role. The deterministic gate `frozen_keys_bound_once` compares DimTrade to the append-only first-encounter key binding and fails closed on any escape. Neither check substitutes for the other.
7. **Review against this Sketch.** Deterministic gates are evidence; Sketch review is a separate acceptance act.

## Projection workaround (not policy)

SQLMesh 0.236.x has no native `MERGE` on DuckDB. Its `INCREMENTAL_BY_UNIQUE_KEY` kind materializes as delete-by-key plus insert of whole rows and raises on a matched-update clause, so it offers no update surface for rule 5 to constrain. DuckDB 1.4+ executes `MERGE INTO` natively and SQLGlot emits it.

The projection therefore uses a `kind CUSTOM` materialization, `governed_merge`, that executes the compiler-built SQLGlot `Merge` through the SQLMesh engine adapter. This is a workaround for a missing tool feature, classified as `sqlmesh_model` projection. It carries no policy: the mutable and frozen column lists it receives are derived from roles by the compiler, and it re-checks them before executing. Retirement trigger: when SQLMesh supports native DuckDB merge with `when_matched`, delete the materialization and run the same guard on the adapter's `Merge`. Nothing in this Sketch changes at that point.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `incremental.authority-locator` | Which TPC-DI 1.1.0 clause governs incremental DimTrade key binding and the mutable surface? | domain reviewer | Reading the specification; replacing the approved decision with a `tpc_di_rule` basis | Recording a presumed clause number |
| `incremental.lifecycle-timestamps` | How are creation and close timestamps assigned from Trade-only CDC rows? | domain reviewer | Named TPC-DI incremental rule or approved counterexample | Reinterpreting `T_DTS` as creation time because the row is first |
| `dim-trade-incremental.other-dimension-keys` | How are security, company, and broker keys bound? | data-product owner | Named rules after those dimensions enter the slice | Guessing from identifiers |
| `source.incremental-cdc-deletes` | How is CDC flag `D` composed into DimTrade? | domain reviewer | Named TPC-DI rule | Inferring from the absence of deletes in the slice |
| `fact-holdings.key-resolution` | Does FactHoldings take keys through the current trade row? | data-product owner | Named TPC-DI rule | Copying whatever DimTrade currently carries |

## Producers

`logical.dim_account` is produced by `dim-account-scd2-v1`, a governed stage of the chain (see `chain-index-v1`). The former hole `dim-account.scd2-source` closed when that Sketch entered the chain.

## Counterexamples

`ce-account-428-rollover-v1` is a constructed counterexample, labeled as such wherever it appears. It exemplifies rules 3 to 5. It was accepted because its general rule names semantic roles and no incident identifiers. It joins `regressions/curated-incremental-v1.json` as `incremental-frozen-key-rebinding-v1`. The phase-1 archive index and regression set are unchanged.

## Artifact and authority separation

- This Sketch and the `mutation_role` values on semantic types govern meaning.
- Source and target schemas are structural anchors only.
- SQLMesh models, the `governed_merge` materialization, SQLGlot ASTs, generated MERGE text, and DuckDB tables are replaceable projections. Successful execution does not make them policy.
- The complete counterexample archive and the curated regression set remain separate artifacts.

## Active repair authority

The data-product-owner hat may authorize changes only through `contracts/incremental/repair-authority/dim-trade-incremental-edge-v1.json`. Its allowed surface is `sketch.edge.trade_cdc_to_dim_trade_incremental`. The DimAccount Sketch, the historical lifecycle edge, all projections, and position metrics are forbidden surfaces. Direct projection edits are rejected and regenerated from this Sketch.
