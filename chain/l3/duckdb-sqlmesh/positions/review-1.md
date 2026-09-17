# Review 1 (sketch reviewer, scoped): positions on duckdb-sqlmesh (verdict: fail)

Scope: cycle-1 projection under `change-contract-1.md`: `manifest.json`, `models/holding_change.sql` (CUSTOM governed_merge), `models/account_position.sql`, `models/customer_position.sql`, six audits. Evidence: check ok; run ok with six audits at zero; two-phase ok with positions keyed only to account 428's 2012 statement; mutate four for four; cross-engine compare identical with duckdb-native.

Reviewer: Opus sketch reviewer, seven scope questions.

## Findings

1. **Read containment and L1.holdings-follow-trade: pass.** holding_change reads only `raw.holding_history` and `governed.trade`; ownership copied as four columns off the trade row; positions read only `governed.holding_change`. Gate enforces declared equals observed reads.
2. **Inner join to governed.trade: authorized for the drop; the review trigger has no way to fire.** The model states twice that a change whose current trade's pin does not resolve drops out of every sum. On this target the upstream `models/trade.sql` itself inner-joins the account and customer pins, so an unresolved pin means no trade row at all and `governed.trade` never carries null ownership. What is not authorized is silence about the other collapsed case: an `hh_t_id` with no trade row, which the handoff and the attribute name as a review trigger. No selected deterministic invariant covers it and the gate rejects audits for unselected invariants, so the Developer could not have added one. Routed as an L2 change (positions cycle 4).
3. **cdc ordering: faithful.** `(cdc_flag IS NOT NULL) DESC, batch_date DESC, cdc_dsn DESC` is equivalent to the native form; the comment names the trap that historical_load synthesizes I only for Trade.txt.
4. **Materialization: exactly right.** unique_key is the identity pair; mutable_columns are exactly the three mutable quantity attributes; frozen_columns exactly the four ownership attributes; quantity_change per the derivation. Gate blind spot recorded: on SQLMesh targets the write guard parses only the SELECT body, so these property lists are not machine-checked against L2 mutation roles. Routed as a gate extension.
5. **Audits: four sound, two defective.** `inv.account_position_not_negative` and `inv.customer_position_not_negative` end at `net_quantity < 0`; a null net_quantity passes silently, where the native sibling adds `OR net_quantity IS NULL`. Not hypothetical: net_quantity is null exactly when every quantity_change in a group is null, the named review trigger of three selected elements. The existing mutation evidence does not cover it because the harness perturbs only frozen and per_statement attributes. `inv.holding_change_not_constructed` (deterministic false) correctly has no audit and the manifest notes it at the artifact; the native manifest lacks that note.
6. **Provenance: pass.** Every derived_from id exists and is selected; sha matches. `derived_from_model.path` names `semantic-model.json`, byte-identical to the selected snapshot at this sha.
7. **Policy decided in SQL: one.** Filtering D from the latest_change set also decides existence: a pair whose only reports are D yields no row. `hole.deletions` reserves that. Defensible, identical on both engines, zero D rows on the fixture; should be stated, not implicit.

Failure class: projection defect, audit sensitivity (two audit files). No authority needed for the fix.

## Cross-engine finding (routed to trade-lifecycle)

Native `trade.sql` LEFT JOINs the pins and keeps a trade whose pin does not resolve with null ownership in four `nullable: false` attributes; SQLMesh `models/trade.sql` inner-joins and drops the trade silently. Same L2, two behaviors, invisible to compare because the fixture has no such trade. Neither is what the L2 says: the pins are non-nullable and the unresolved pin is a review trigger. Routed as trade-lifecycle cycle 8 (invariants that make either behavior a violation) and a constructed counterexample proposal, `ce.l2.trade-before-account-statement`.

## Routed items

- L2 positions cycle 4: invariant making unresolved current_trade_number checkable; invariant that before_qty, after_qty, quantity_change are never null on holding_change; hole.deletions to name row existence.
- Gate: cross-check SQLMesh materialization_properties against L2 mutation roles.
- Harness: mutate non-nullable mutable attributes and derived attributes, not only frozen and per_statement.

Rejected artifacts: `audits/inv.account_position_not_negative.sql`, `audits/inv.customer_position_not_negative.sql`. Models and the other four audits stand pending the L2 change.
