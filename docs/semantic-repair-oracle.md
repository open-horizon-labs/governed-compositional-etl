# Semantic repair oracle v1

Issue #3 freezes the location and repair authority for a deliberately small pilot corpus before any experiment arm sees a failure. The oracle is a research instrument for the bounded spike, not a claim of complete TPC-DI coverage or benchmark compliance.

## Authority boundary

The corrected meaning in each case is authorized by a named TPC-DI 1.1.0 rule or an approved decision. Source values and table shapes are supporting evidence only; they do not authorize a transformation. An unknown rule stays a Sketch hole and is not made scorable by guessing.

The retained source anchors are in [`evidence/issue-3/source-anchors-v1.json`](../evidence/issue-3/source-anchors-v1.json). The local and edge cases use these TPC-DI 1.1.0 rules:

- Clauses 2.2.2.13 and 2.2.2.18 define the status and trade-type reference fields.
- Clause 2.2.2.16 defines the historical status observations and their update timestamps.
- Clause 4.5.8.1 composes historical `Trade` and `TradeHistory` rows by trade identifier.
- Clause 4.5.8.2 obtains DimTrade reference names and selects creation/close times from status-qualified history timestamps.

The [oracle-substrate decision](../.oh/metis/issue-3-oracle-substrate-decision.md) provisionally accepts PR #9's pinned redistribution and four-file slice for internal oracle construction. Canonical registered-package hash comparison and current license/fair-use review remain human gates before external publication.

## Frozen formats and cases

`oracle/schema/failure-fixture-v1.schema.json` is the versioned fixture contract. Every fixture carries its inputs, observed and corrected outputs, failure class, earliest responsible location, authority, allowed and forbidden artifacts, tempting wrong repair, affected descendants, and opaque held-out neighbors. `oracle/schema/repair-submission-v1.schema.json` is the separate structural answer format.

The public pilot corpus freezes:

1. A local semantic failure: a trade-type identifier (`TMS`) escapes reference interpretation instead of producing `Market Sell`.
2. An edge/composition failure: valid Trade and TradeHistory stage outputs compose using `Trade.T_DTS` for historical creation time instead of the `SBMT`-qualified `TradeHistory.TH_DTS` required by clause 4.5.8.2.
3. An ambiguous failure: an observed status identifier leak does not reveal whether the reference stage or its outgoing edge first made the wrong choice. No repair artifact is authorized until intermediate evidence resolves the boundary.

The edge case is a candidate for the later matched experiment. Its oracle label is genuine at this stage because both producer records remain valid in isolation and the named rule is violated only by their composition. Issue #7 must still demonstrate that the three experiment arms encounter equivalent seeded failures.

## Narrative-free scoring

A submission contains only location, class, changed artifact identifiers, corrected output, and the descendants actually revalidated. Additional keys—including `explanation` or `repair_narrative`—are invalid. The scorer compares those fields mechanically and verifies that every changed artifact is authorized and no forbidden projection was patched.

Run the retained examples and all fixture checks:

```sh
python3 scripts/oracle.py verify
```

Score one public submission:

```sh
python3 scripts/oracle.py score \
  --fixture oracle/fixtures/public/edge-trade-history-create-time-v1.json \
  --submission oracle/submissions/examples/edge-trade-history-create-time-v1.json
```

## Held-outs

The public corpus enumerates opaque held-out IDs and relationships, but contains no held-out inputs, corrected outputs, or labels. Actual held-out fixtures belong in the Git-ignored `oracle/fixtures/held-out/` directory and must be disclosed only to the evaluator after the repair is frozen. Their neighboring relation is chosen during adjudication, not generated from raw similarity.

`score-sealed` accepts only fixtures marked `held_out`, requires their case IDs to exactly match the frozen corpus reservations, and emits aggregate counts—never case IDs, expected locations, corrected outputs, or dimension-level failures:

```sh
python3 scripts/oracle.py score-sealed \
  --fixture-dir oracle/fixtures/held-out \
  --submission-dir /path/to/frozen/submissions
```

This separation protects the held-outs from visible scoring. A research-sponsor adoption decision must not treat the public example scores as held-out evidence.

## Adjudication protocol

The domain-reviewer hat owns semantic labels; the experiment-lead hat owns corpus mechanics and arm fairness. Before a fixture is marked `adjudicated`, reviewers independently record a proposed failure class, earliest responsible stage/edge/path invariant, named authority, permitted policy or implementation artifact, forbidden repairs, affected descendants, and neighboring held-outs. Repair narratives are hidden during this pass.

Agreement requires the same named authority, failure class, earliest location, authorized artifact set, and downstream cone. Cosmetic wording differences do not count as disagreement. When proposals differ:

1. Reproduce the observation and expose only the intermediate evidence needed to distinguish the proposed boundaries.
2. Check the named rule or approved decision; raw values, schemas, generated SQL, and DuckDB results may falsify an implementation but may not supply missing policy.
3. Prefer the earliest boundary whose contract can be shown wrong while its inputs remain valid. A later symptom is never selected merely because it is easiest to patch.
4. If the evidence resolves the dispute, record the alternatives, evidence, decision hat, and justification in a repository-native decision record, then update the fixture version before any arm sees it.
5. If two or more locations remain defensible, set `disposition` and `failure_class` to `ambiguous`, retain every candidate location, authorize no repair artifact, and exclude the case from location-effect estimates. Ambiguity is a result, not a forced stage label.

The issue review trigger fires if independent labels change after this process or if the edge case reduces to an ordinary local defect. In that event, freeze experiment execution, preserve both label sets, and reframe the corpus rather than tuning the scorer post hoc.
