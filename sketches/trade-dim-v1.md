---
id: trade-dim-v1
status: incomplete
owner_hat: data-product-owner
authority: TPC-DI-1.1.0
---

# Trade dimension Sketch v1

This is the human-reviewable governing Sketch for the four-file historical trade slice. It is intentionally incomplete. A raw value, a source or target column, a generated query, or a materialized table may expose a hole but cannot fill it.

## Grain and identity

- `stage.trade`: one record per `Trade.T_ID`; `trade_id` is stable identity.
- `stage.trade_history`: one status observation per `(TH_T_ID, TH_DTS, TH_ST_ID)`.
- `logical.dim_trade`: one historical warehouse record per `trade_id` in this bounded slice.

## Known rules in order

1. **Anchor structure only.** Parse the four issue #2 sources according to their declared fields. This step authorizes no classification or default.
2. **Preserve local timestamp meaning.** Map `Trade.T_DTS` to semantic type `trade_record_timestamp`; do not rename it `created_at`. Map each `TradeHistory.TH_DTS` to `status_update_timestamp` together with its status.
3. **Interpret named references.** Resolve trade `Type` from `TradeType.TT_NAME` by identifier and `Status` from `StatusType.ST_NAME` by identifier. Authority: TPC-DI 1.1.0 clause 4.5.8.2.
4. **Compose lifecycle identity.** Join Trade and TradeHistory by the trade identifier. Authority: clause 4.5.8.1.
5. **Select creation time at the edge.** For market buy/sell (`TMB`, `TMS`), select the `SBMT` history timestamp. For the remaining historical path, select the `PNDG` timestamp. Assign semantic type `trade_creation_timestamp`. Authority: clause 4.5.8.2.
6. **Select close time at the edge.** Select the `CMPT` or `CNCL` history timestamp and assign semantic type `trade_close_timestamp`. Authority: clause 4.5.8.2.
7. **Emit the logical record.** The consumer may copy an already typed lifecycle handoff; it may not reinterpret `trade_record_timestamp` as `trade_creation_timestamp` merely because both are SQL timestamps.
8. **Verify twice.** Run deterministic approved-output gates, then review the result against this current Sketch. Neither check substitutes for the other.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `source.incremental-cdc` | How do Trade-only incremental updates compose with historical history? | domain reviewer | Named TPC-DI incremental rule or approved counterexample | Raw CDC patterns, target columns, generated SQL |
| `edge.incremental-update-lifecycle` | How does the historical history-based handoff compose with incremental Trade-only updates? | domain reviewer | Named TPC-DI incremental rule or approved counterexample | Reusing the historical edge because its fields happen to fit |
| `dim-trade.security-account-keys` | Which effective-dated security, company, account, customer, and broker keys apply? | data-product owner | Named rules after those sources enter the slice | Guessing from identifiers or foreign-key shape |
| `dim-trade-consumer.out-of-slice-keys` | How are the out-of-slice surrogate keys supplied to the DimTrade consumer? | data-product owner | The approved resolution of the effective-dated key rules | Inventing placeholders from target nullability or defaults |
| `dim-trade.batch-id` | How is BatchID assigned in the executable projection? | data-product owner | Named TPC-DI batch rule | Using the database default |
| `trade-stage.execution-pricing-policy` | Which price fields participate in measures beyond direct copy? | domain reviewer | Named rule or approved counterexample | Deriving a plausible financial formula from values |

Until resolved, each hole remains `open`, has no compiled policy body, and cannot be repaired by editing an adjacent rule.

## Artifact and authority separation

- This Sketch governs the known business meaning.
- Source and target schemas are structural anchors only.
- Accepted counterexamples may revise this Sketch after review; the complete archive and curated regression set remain separate artifacts.
- SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections. They never become policy authority through successful execution.
- Deterministic gates are evidence. Sketch review is a separate acceptance act.

## Active repair authority

The data-product-owner hat may authorize changes only through the records under `contracts/repair-authority/`. Conflicts with named domain authority stop for adjudication. Direct projection edits are rejected and regenerated from the approved Sketch.
