---
id: dim-account-scd2-v1
status: incomplete
owner_hat: data-product-owner
authority: issue-8-scd2-versioning-adjudication (assumed; TPC-DI-1.1.0 locator unverified)
chain_position: 2
depends_on: dim-customer-scd2-v1
---

# DimAccount SCD2 Sketch v1

Governs account versions from Batch1 CustomerMgmt actions, incremental Account CDC, customer-version propagation, and a labeled counterexample stage. It is intentionally incomplete.

## Grain and identity

- `stage.account_cdc`: one change record per `(CA_ID, CDC_DSN)` per batch.
- `stage.account_change_ce`: constructed account changes; every row carries provenance `controlled_counterexample`.
- `logical.dim_account`: one row per account version `(account_id, effective_from)`; `sk_account_id` is assigned once per version and is the value DimTrade freezes at first encounter.

## Known rules in order

1. **Anchor structure only.** Same field-minimal extraction as DimCustomer. `CA_NAME` stays out.
2. **One version per change event.** NEW, ADDACCT, UPDACCT, CLOSEACCT and every CDC row create an account version at their event time; CDC rows version at the batch date. Authority: `issue-8-scd2-versioning-adjudication` (assumed).
3. **Status from action.** CLOSEACCT yields `INAC`; other actions yield `ACTV`. Tax status and customer carry forward when a change omits them.
4. **Propagate customer versions.** A new customer version re-versions every account of that customer open at that time. Each account version resolves `sk_customer_id` from the customer version effective as of its own `effective_from`.
5. **Assign ordinal surrogate keys and close previous versions.** Same policy as DimCustomer. Exactly one current version per account; versions do not overlap.
6. **Admit the labeled counterexample stage.** Rows from `stage.account_change_ce` join the change feed with their provenance intact. They never enter raw files. A projection that reads counterexample rows from raw is rejected.
7. **Verify twice.** Deterministic gates `one_current_version_per_account` and `versions_do_not_overlap`; then review against this Sketch.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `dim-account.broker-key` | How is SK_BrokerID resolved? | data-product owner | Named rule once DimBroker enters the slice | Copying CA_B_ID as a key |
| `dim-account.account-desc-attributes` | Does CA_NAME version the dimension? | domain reviewer | Named TPC-DI DimAccount rule | Assuming from the target schema |
| `edge.account.cdc-timestamp` | Does a CDC row version at the batch date? | domain reviewer | Named TPC-DI incremental rule | Inventing a timestamp |

## Counterexamples

`ce-account-428-rollover-v1` supplies one constructed change for account 428 at 2017-07-08 00:58:00. It enters through rule 6 only.

## Artifact and authority separation

This Sketch and the semantic-type roles govern meaning. SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables are replaceable projections. Repair authority: `contracts/incremental/repair-authority/dim-account-scd2-edge-v1.json`.
