---
id: dim-customer-scd2-v1
status: incomplete
owner_hat: data-product-owner
authority: issue-8-scd2-versioning-adjudication (assumed; TPC-DI-1.1.0 locator unverified)
chain_position: 1
---

# DimCustomer SCD2 Sketch v1 (stub)

Governs customer versions from Batch1 CustomerMgmt actions and incremental Customer CDC. Deliberately a stub: only status and tier version the dimension. It is intentionally incomplete.

## Grain and identity

- `stage.customer_mgmt_action`: one row per CustomerMgmt action.
- `stage.customer_cdc`: one change record per `(C_ID, CDC_DSN)` per batch.
- `logical.dim_customer`: one row per customer version `(customer_id, effective_from)`; `sk_customer_id` is assigned once per version.

## Known rules in order

1. **Anchor structure only.** Extract the field-minimal action set: type, timestamp, customer id, account id, broker id, tax status, tier. Names, addresses, contacts, and tax ids stay out of the slice.
2. **One version per change event.** NEW, UPDCUST, and INACT actions and every CDC row create a customer version at their event time. CDC rows version at the batch date. Authority: `issue-8-scd2-versioning-adjudication` (assumed).
3. **Status from action.** INACT yields `INAC`; NEW and UPDCUST yield `ACTV`. CDC rows carry their own status. Tier carries forward when a change omits it.
4. **Assign ordinal surrogate keys.** `sk_customer_id` is the ordinal over `(effective_from, customer_id)` across the complete feed. This is a bounded-slice assignment policy, not a TPC-DI rule.
5. **Close the previous version.** `effective_to` is the next version's `effective_from`; 9999-12-31 while current. Exactly one current version per customer.
6. **Verify twice.** Deterministic gate `one_current_version_per_customer`; then review against this Sketch.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `dim-customer.attributes-beyond-status` | Which attributes version the dimension beyond status and tier? | data-product owner | Named TPC-DI DimCustomer rules | Copying every XML field because it is present |
| `edge.customer.cdc-timestamp` | Does a CDC row version at the batch date? | domain reviewer | Named TPC-DI incremental rule | Inventing a timestamp from CDC_DSN |
| `scd2.authority-locator` | Which clauses govern DimCustomer and DimAccount loading? | domain reviewer | Reading the specification | Recording a presumed clause number |

## Artifact and authority separation

This Sketch and the semantic-type roles govern meaning. SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections. Repair authority: `contracts/incremental/repair-authority/dim-account-scd2-edge-v1.json`.
