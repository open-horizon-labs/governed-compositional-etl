---
id: issue-8-scd2-versioning-adjudication
title: "Presume SCD2 versioning rules for DimCustomer and DimAccount under an approved decision"
outcome: governed-compositional-etl-repair
status: assumed-pending-spec-read
---

# SCD2 versioning adjudication

**Date:** 2026-09-16

**Decision hats:** domain-reviewer for meaning; data-product-owner for repair scope.

## Evidence

- Batch1 CustomerMgmt.xml holds 14,573 actions in six types: NEW 4728, ADDACCT 4280, UPDACCT 2568, UPDCUST 1284, CLOSEACCT 1284, INACT 428. Customer and Account elements are un-namespaced children of the namespaced Action element.
- Customer 238: NEW 2007-12-29 with account 428 (tax status 1, broker 7114, tier 3); ADDACCT 624 2008-03-14; INACT 2008-03-23; UPDACCT 624 2010-02-07; CLOSEACCT 428 2012-11-15. Account 428 has no Batch2 or Batch3 CDC rows.
- Batch2 Account CDC has 30 rows (27 ACTV, 3 INAC) with no timestamp column; Customer CDC has 15 rows.
- The TPC-DI 1.1.0 specification text for DimCustomer and DimAccount historical and incremental loading has not been read here.

## Choices

1. Record presumed clause numbers as verified authority.
2. Build nothing until the specification is read.
3. Record this decision as the basis, mark the derived rules `assumed`, keep locator holes open, and swap to verified `tpc_di_rule` bases after the read.
4. Let the projection's convenient shape define the versioning.

## Decision

Under the domain-reviewer hat, choose option 3. The presumed rules are:

- Every change event creates a new version of its natural identity. Customer events: NEW, UPDCUST, INACT. Account events: NEW, ADDACCT, UPDACCT, CLOSEACCT.
- Status derives from the action: INACT and CLOSEACCT yield `INAC`; other actions yield `ACTV`. CDC rows carry their own status.
- A new customer version re-versions every account of that customer open at that time, and each account version resolves `sk_customer_id` from the customer version effective as of its own `effective_from`.
- A version starts at its change event time and ends at the next version's start; 9999-12-31 while current. Incremental CDC rows version at the batch date. That choice is a hole (`edge.*.cdc-timestamp`) because the CDC files carry no timestamp.
- Surrogate keys are ordinals over (effective_from, natural id) across the complete change feed. This is a deterministic assignment policy for the bounded slice, not a TPC-DI rule.
- Fact-like rows resolve dimension versions as of their own event time at first encounter. DimTrade resolves the account version as of `T_DTS`; FactHoldings takes keys from the DimTrade row of its current trade and never re-resolves.

Constructed account changes enter through a stage whose every row is labeled `controlled_counterexample`. They never enter raw files.

## Review trigger

Reading the TPC-DI 1.1.0 DimCustomer, DimAccount, DimTrade incremental, and FactHoldings clauses. Any rule the specification states differently flips to `rejected`, its counterexamples are re-adjudicated, and the projection is regenerated.

## Addendum, 2026-09-17: anchor the historical trade history

A projection reviewer found that the chain's source anchors omitted Batch1 TradeHistory.txt, so a historical-load trade's earliest held report was its snapshot row with its final status. Real rows: trade 353232 was pending on 2017-01-12 14:55:11, submitted 2017-04-10 20:25:00, completed 20:26:42; the chain had placed it at completion. Under the data-architect hat, anchor `raw.trade_history` as shape and state in `report_order` that a historical-load trade's held reports include its TradeHistory rows. No clause changes: L1.placement-moment already says "the earliest report of it the brokerage holds"; the anchors under-stated what is held. Consequence: trade-lifecycle L2 cycle 5 adds the history handoff for placed_at and lets first_seen_late consider it; the cache should stale sg.placement-moment only. Proposal `ce.k.trade-history-not-anchored` accepted as this addendum.
