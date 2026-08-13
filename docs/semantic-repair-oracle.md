# Semantic repair oracle v1

Issue #3 freezes the available location evidence and repair authority for a deliberately small pilot corpus before any experiment arm sees a failure. Adjudicated locations are exact; unresolved locations remain explicit candidates with no authorized repair. The oracle is a research instrument for the bounded spike, not a claim of complete TPC-DI coverage or benchmark compliance.

## Authority boundary

The corrected meaning in each case is authorized by a named TPC-DI 1.1.0 rule or an approved decision. Source values and table shapes are supporting evidence only; they do not authorize a transformation. An unknown rule stays a Sketch hole and is not made scorable by guessing.

The retained source anchors are in [`evidence/issue-3/source-anchors-v1.json`](../evidence/issue-3/source-anchors-v1.json). The local and candidate composition cases use these TPC-DI 1.1.0 rules:

- Clauses 2.2.2.13 and 2.2.2.18 define the status and trade-type reference fields.
- Clause 2.2.2.16 defines the historical status observations and their update timestamps.
- Clause 4.5.8.1 composes historical `Trade` and `TradeHistory` rows by trade identifier.
- Clause 4.5.8.2 obtains DimTrade reference names and selects creation/close times from status-qualified history timestamps.

The [oracle-substrate decision](../.oh/metis/issue-3-oracle-substrate-decision.md) provisionally accepts PR #9's pinned redistribution and four-file slice for internal oracle construction. Canonical registered-package hash comparison and current license/fair-use review remain human gates before external publication.

## Frozen formats and cases

`oracle/schema/failure-fixture-v1.schema.json` is the versioned fixture contract. Every fixture carries its inputs, observed and corrected outputs, failure class, adjudicated location or unresolved candidates, authority, allowed and forbidden artifacts, tempting wrong repair, affected descendants, and opaque held-out neighbors. `oracle/schema/repair-submission-v1.schema.json` is the separate structural answer format.

The public pilot corpus freezes:

1. A local semantic failure: a trade-type identifier (`TMS`) escapes reference interpretation instead of producing `Market Sell`.
2. A candidate edge/composition failure: the observed historical output uses `Trade.T_DTS` for creation time instead of the `SBMT`-qualified `TradeHistory.TH_DTS` required by clause 4.5.8.2. The corrected output is authority-backed, but the earliest responsible boundary is not yet adjudicated.
3. An ambiguous failure: an observed status identifier leak does not reveal whether the reference stage or its outgoing edge first made the wrong choice. No repair artifact is authorized until intermediate evidence resolves the boundary.

The candidate is deliberately classified `candidate_edge_composition` with an ambiguous location spanning the Trade stage, TradeHistory stage, and their handoff. It authorizes no repair. Issue #4 must define and apply the local contracts before reviewers can determine whether the case survives as an edge/composition failure or reduces to a local semantic defect. The edge-risk review trigger remains pending—not fired and not retired. Issue #7 must separately demonstrate equivalent seeds across experiment arms.

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

The public corpus retains each opaque held-out ID, relationship, fixture schema version, and canonical SHA-256. Those commitments freeze four actual fixtures without exposing their inputs, corrected outputs, or labels. The plaintext fixtures are in the Git-ignored `oracle/fixtures/held-out/` private-custody directory; reference answers used only to verify the scorer are likewise ignored under `oracle/submissions/held-out/`.

The committed hashes make any later fixture change detectable, but they cannot reproduce confidential contents from a fresh clone. Custody therefore has two parts: Git preserves the immutable commitments, while the experiment custodian must preserve and transfer the exact private files out of band. There is intentionally no public materialization command because a deterministic generator would disclose or make derivable the held-out answers. Loss of private custody invalidates held-out evaluation; it does not authorize creating replacement cases under the old commitments.

`score-sealed` verifies every private fixture byte-for-byte against its public commitment, rejects missing or extra cases, accepts only fixtures marked `held_out`, and emits aggregate counts—never case IDs, expected locations, corrected outputs, or dimension-level failures:

```sh
python3 scripts/oracle.py score-sealed \
  --fixture-dir oracle/fixtures/held-out \
  --submission-dir oracle/submissions/held-out
```

This separation protects the held-outs from visible scoring. A research-sponsor adoption decision must not treat the public example scores as held-out evidence.

## Adjudication protocol

The domain-reviewer hat owns semantic labels; the experiment-lead hat owns corpus mechanics and arm fairness. Before a fixture is marked `adjudicated`, reviewers independently record a proposed failure class, earliest responsible stage/edge/path invariant, named authority, permitted policy or implementation artifact, forbidden repairs, affected descendants, and neighboring held-outs. Repair narratives are hidden during this pass.

Agreement requires the same named authority, failure class, earliest location, authorized artifact set, and downstream cone. Cosmetic wording differences do not count as disagreement. When proposals differ:

1. Reproduce the observation and expose only the intermediate evidence needed to distinguish the proposed boundaries.
2. Check the named rule or approved decision; raw values, schemas, generated SQL, and DuckDB results may falsify an implementation but may not supply missing policy.
3. Prefer the earliest boundary whose contract can be shown wrong while its inputs remain valid. A later symptom is never selected merely because it is easiest to patch.
4. If the evidence resolves the dispute, record the alternatives, evidence, decision hat, and justification in a repository-native decision record, then update the fixture version before any arm sees it.
5. If two or more locations remain defensible, set `disposition` to `ambiguous`, retain every candidate location, authorize no repair artifact, and exclude the case from location-effect estimates. Use `failure_class: ambiguous` when even the class is unresolved; retain `candidate_edge_composition` only when the authority-backed output qualifies it for issue #4 edge-versus-local adjudication. Ambiguity is a result, not a forced stage label.

Issue #4 is the planned adjudication point for the candidate boundary. The review trigger remains pending while those local contracts are absent. It fires if contract-backed reviewers cannot stabilize the boundary or if the candidate reduces to an ordinary local defect; that evidence must be preserved and the corpus reframed rather than tuned post hoc.
