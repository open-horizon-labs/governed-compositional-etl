---
id: chain-index-v1
status: incomplete
owner_hat: data-product-owner
---

# Chain index v1

One Sketch per stage, one edge owner per hole. Repair authority records name per-Sketch artifacts, so a single chained Sketch is rejected.

| Position | Sketch | Produces | Edge contract | Repair authority |
|---|---|---|---|---|
| 1 | `dim-customer-scd2-v1` | `logical.dim_customer` | `edge.change_feeds_to_dim_customer.v1` | `repair.dim-account-scd2-edge.v1` |
| 2 | `dim-account-scd2-v1` | `logical.dim_account` | `edge.change_feeds_to_dim_account.v1` | `repair.dim-account-scd2-edge.v1` |
| 3 | `trade-dim-incremental-v1` (extends `trade-dim-v1`) | `logical.dim_trade_incremental` | `edge.trade_cdc_to_dim_trade_incremental.v1` | `repair.dim-trade-incremental-edge.v1` |
| 4 | `fact-holdings-v1` | `logical.fact_holdings` | `edge.holding_history_to_fact_holdings.v1` | `repair.fact-holdings-edge.v1` |
| 5 | `position-metrics-v1` | `logical.position_by_account`, `logical.position_by_customer` | `edge.fact_holdings_to_position_metrics.v1` | none; metrics are forbidden repair surfaces |

Mutation roles live once, on semantic types in `contracts/incremental/semantic-types/`. `account_surrogate_key` and `customer_surrogate_key` are `frozen_from_first_encounter` in every consumer. The revalidation profile v2 is compiled from the edge contracts' typed mappings; the affected list in a diagnosis is computed, never a constant.

Counterexamples: `ce-account-428-rollover-v1` (constructed, labeled) enters through `stage.account_change_ce` at position 2 and is caught at positions 3 and 4 by the guard, at position 5 by the invariant.

## Seams are mechanical, not declared

A link is part of the chain only if the harness enforces its seams:

1. **Handoff binding.** Every edge mapping whose source is a producer logical model or stage must resolve to an attribute of that producer with the identical semantic type. A consumer may not declare a type for a producer's output.
2. **Read containment.** A governed model body may reference only the entities its edge contract names as producers or references. FactHoldings may read `holding_history_stage` and `dim_trade_incremental`; a direct join to `dim_account` to re-resolve keys is rejected before plan. That is the tempting wrong repair at link 4.
3. **Cone-driven gates.** A violation at a node selects downstream gates from the revalidation profile; the report runs those, not everything.
4. **Composite acceptance.** `accepted(chain, case)` holds only when every link passes its deterministic gates and its sketch review on the active case and the curated regressions, and the path invariants at link 5 hold.

## Phase-1 holes this chain addresses

`trade-dim-v1` is frozen (its bytes are pinned by the phase-1 compiler profile) and its hole rows are not edited. Under `issue-8-incremental-key-binding-adjudication` (assumed), `trade-dim-incremental-v1` addresses `source.incremental-cdc`, `edge.incremental-update-lifecycle`, and `dim-trade.security-account-keys` for account and customer keys only. `dim-trade-consumer.out-of-slice-keys`, `dim-trade.batch-id`, and `trade-stage.execution-pricing-policy` remain open in both Sketches.
