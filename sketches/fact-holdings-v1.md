---
id: fact-holdings-v1
status: incomplete
owner_hat: data-product-owner
authority: issue-8-incremental-key-binding-adjudication (assumed; TPC-DI-1.1.0 locator unverified)
chain_position: 4
depends_on: trade-dim-incremental-v1
---

# FactHoldings Sketch v1

Governs holding changes from HoldingHistory into FactHoldings, taking dimension keys through the current trade. It is the second consumer of the `frozen_from_first_encounter` role. It is intentionally incomplete.

## Grain and identity

- `stage.holding_history`: one holding change per `(HH_H_T_ID, HH_T_ID)`.
- `logical.fact_holdings`: one row per holding change `(original_trade_id, current_trade_id)`.

## Known rules in order

1. **Anchor structure only.** Copy original trade id, current trade id, before and after quantities, and the CDC sequence when present.
2. **Match on both trade identities.** A holding change is identified by its original and current trade ids together.
3. **Resolve keys through the current trade.** `sk_account_id` and `sk_customer_id` come from the DimTrade row whose `trade_id` equals `current_trade_id`. FactHoldings never re-resolves keys against DimAccount or DimCustomer. Authority: `issue-8-incremental-key-binding-adjudication` (assumed).
4. **Emit the write as a MERGE whose matched-update set is exactly the mutable-role columns.** Quantities are mutable; the keys are `frozen_from_first_encounter` by their semantic type. The same guard that protects DimTrade protects this table without a new rule.
5. **Verify twice.** AST guard before plan; deterministic gate `frozen_keys_bound_once` after run; then review against this Sketch.

## Projection workaround (not policy)

Same as `trade-dim-incremental-v1`: the `governed_merge` custom materialization executes the compiler-built MERGE because SQLMesh has no native DuckDB merge. Retirement trigger: native support with `when_matched`.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `fact-holdings.key-resolution-authority` | Which clause states keys come from the current trade's DimTrade row? | data-product owner | Reading the specification | Recording a presumed clause number |
| `fact-holdings.security-company-keys` | How are SK_SecurityID and SK_CompanyID resolved? | data-product owner | Named rules once those dimensions enter | Guessing from the symbol |
| `fact-holdings.price-and-date-keys` | How are CurrentPrice, SK_DateID, SK_TimeID assigned? | domain reviewer | Named TPC-DI rule | Copying the trade price |

## Artifact and authority separation

This Sketch and the semantic-type roles govern meaning. Projections are replaceable. Repair authority: `contracts/incremental/repair-authority/fact-holdings-edge-v1.json`.
