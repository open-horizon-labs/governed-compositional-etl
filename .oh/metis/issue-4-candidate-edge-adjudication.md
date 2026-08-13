---
id: issue-4-candidate-edge-adjudication
title: "Adjudicate the historical trade creation-time failure at the handoff"
outcome: governed-compositional-etl-repair
---

# Candidate edge adjudication

**Date:** 2026-08-13

**Decision hats:** data architect for boundary classification; data-product owner for repair authority

**Issues:** #3 and #4

**Status:** adjudicated for the bounded historical slice

## Evidence

TPC-DI 1.1.0 clause 4.5.8.1 composes historical Trade and TradeHistory by trade identifier. Clause 4.5.8.2 selects creation and close times from status-qualified `TradeHistory.TH_DTS`.

The independent issue #4 checks retain distinct local meanings:

- the Trade producer copies `T_DTS` as `trade_record_timestamp` and passes its local mapping check;
- the TradeHistory producer copies each `TH_DTS` as `status_update_timestamp` with its status and passes its local mapping check;
- the DimTrade consumer copies the supplied, typed lifecycle handoff and passes its local copy and time-order checks;
- the handoff incorrectly binds `trade_record_timestamp` to the consumer's `trade_creation_timestamp`; both are physical `TIMESTAMP` values, but their nominal meanings differ, and the observed timestamp is not the `SBMT` history timestamp required by clause 4.5.8.2.

`scripts/contracts.py verify` recomputes these checks from the contracts and `evidence/issue-4/candidate-edge-check-v1.json`, then requires the result to equal the retained adjudication.

## Choices

1. Classify the failure at the Trade producer by treating `T_DTS` as creation time.
2. Classify it at the DimTrade consumer because the incorrect value is visible there.
3. Classify it at the Trade/TradeHistory lifecycle handoff, where the wrong semantic type and source timestamp are selected despite valid local producer and consumer behavior.
4. Leave it ambiguous if independent local checks cannot isolate the boundary.

## Decision

Under the data-architect hat, choose option 3. This is a genuine bounded edge/composition failure: independent producer and consumer checks pass, while the named composition contract fails. This retires the current edge-versus-local risk for this historical case only; it does not generalize to other lifecycle paths or incremental updates.

Under the data-product-owner hat, authorize changes only to `sketch.edge.trade_history_to_dim_trade`. Stage Sketches, generated SQL, SQLMesh models, SQLGlot ASTs, DuckDB tables, and downstream metrics remain forbidden repair surfaces. Authority conflicts stop for domain review; projections are regenerated rather than hand-patched.
