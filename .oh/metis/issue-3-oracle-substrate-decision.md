---
id: issue-3-oracle-substrate-decision
title: "Provisionally accept the issue #2 slice for oracle construction"
outcome: governed-compositional-etl-repair
---

# Oracle substrate decision

**Date:** 2026-08-13

**Decision hats:** domain reviewer and experiment lead

**Issue:** #3

**Status:** assumed for the bounded spike

## Evidence considered

PR #9 pins a redistribution that identifies itself as TPC-DI DIGen 1.1.0, verifies its core tool hashes before execution, and retains deterministic hashes and row counts for the generated scale-factor-3 slice. The selected `StatusType`, `TradeType`, `Trade`, and `TradeHistory` files contain the source records named by TPC-DI 1.1.0 clauses 4.5.8.1 and 4.5.8.2 for the bounded DimTrade historical-load rules used by this pilot.

The retained source rows provide direct examples of reference-name interpretation and the composition of trade rows with ordered status history. They are enough to construct one local semantic failure, one edge/composition failure, and one deliberately ambiguous diagnostic case without inventing business policy.

The remaining provenance caveat is unchanged: the evaluated redistribution has not yet been compared with a personally acquired canonical registered TPC package, and current license and fair-use terms still require human review.

## Choices

1. Stop oracle construction until canonical-package and license review is complete.
2. Expand the source slice before freezing any cases.
3. Accept PR #9's pinned redistribution and four-file slice provisionally for internal spike/oracle construction, while keeping canonical hash and license confirmation as a publication gate.

## Assumed decision

Under the domain-reviewer hat, choose option 3: the named TPC-DI transformation clauses, not raw values or table shapes, authorize the oracle labels and corrected outputs. The four files are provisionally adequate for the pilot cases.

Under the experiment-lead hat, continue the spike on that basis. Personally acquiring the canonical TPC-DI 1.1.0 package, comparing the relevant hashes, and reviewing current TPC/PDGF license and fair-use terms remain mandatory before external publication or any workload-fidelity claim. They are not blockers for internal oracle construction. This decision neither calls the experiment a compliant benchmark nor broadens the slice.
