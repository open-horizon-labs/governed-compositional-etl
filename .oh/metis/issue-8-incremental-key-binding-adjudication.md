---
id: issue-8-incremental-key-binding-adjudication
title: "Presume first-encounter key binding for incremental DimTrade under an approved decision"
outcome: governed-compositional-etl-repair
status: assumed-pending-spec-read
---

# Incremental key binding adjudication

**Date:** 2026-09-16

**Decision hats:** domain-reviewer for meaning; data-product-owner for repair scope; data-architect for the role vocabulary.

**Phase:** 2 (chained lifecycle example)

## Evidence

- Trade 372101 was first encountered in Batch1 as `PNDG` on account 428 and completes in Batch2 through CDC rows `SBMT` then `CMPT`.
- Trade 353232 (Batch1, same account and security) is closed through 372101 in Batch2 HoldingHistory, so any rebinding of 372101's account key propagates into holdings.
- No Batch2 or Batch3 Account CDC row exists for account 428. The rollover in `counterexamples/archive/ce-account-428-rollover-v1.json` is constructed and labeled.
- The TPC-DI 1.1.0 specification text for incremental DimTrade and FactHoldings has not been read in this repository. Its clause locator is therefore not recorded as a `tpc_di_rule` authority. Recording a presumed clause number would fabricate authority.

## Choices

1. Fill the hole with a presumed clause number as if verified.
2. Leave the hole open and build nothing until the specification is read.
3. Record this decision as the authority basis, mark the derived rules `assumed`, keep a hole `incremental.authority-locator` open, and replace the basis with a verified `tpc_di_rule` when the clause is read.
4. Let the constructed counterexample alone authorize the rule.

## Decision

Under the domain-reviewer hat, choose option 3. The rule adopted is general and stated through semantic roles: a surrogate key on a fact-like dimension row is `frozen_from_first_encounter`; lifecycle fields are `mutable`; the matched-update surface of any incremental write is exactly the mutable-role columns. Option 4 is rejected because a constructed counterexample exemplifies a rule but does not authorize it; it is accepted into the archive only because its general rule names no incident identifiers.

Under the data-architect hat, add `mutation_role` to semantic types (schema `semantic-types/v2`) with values `none`, `identity`, `mutable`, `frozen_from_first_encounter`. Roles attach to types. A contract that places a role on a column name is rejected.

Under the data-product-owner hat, authorize repair only through `sketch.edge.trade_cdc_to_dim_trade_incremental` per `contracts/incremental/repair-authority/dim-trade-incremental-edge-v1.json`.

## Review trigger

Reading TPC-DI 1.1.0 incremental DimTrade and FactHoldings clauses. If the specification binds keys differently, the rules flip to `rejected`, the counterexample is re-adjudicated, and the projection is regenerated. If it confirms, the `assumed` rules become `known` and this record becomes supporting evidence rather than the basis.
