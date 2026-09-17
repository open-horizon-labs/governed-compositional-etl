# Review 3 (sketch reviewer, scoped): positions on duckdb-native, L3 cycle 3 (verdict: fail, narrow)

Scope: the cycle-3 change under `change-contract-3.md`: one new audit (`inv.eligible_holding_report_persisted`), the cardinality branch in both sum audits, candidate-filter phrasing "aligned" across the projection and two audits, manifest provenance and note. Evidence: check status question, zero problems, 13 audits; run ok, 13 at zero; two-phase ok; mutate 14, zero unprotected; the tie counterexample silent.

Reviewer: Opus sketch reviewer, seven scope questions.

## Rejected artifacts

`holding_change.sql` (the `latest_report` candidate filter and the header sentences) and `audits/inv.holding_quantity_updates_in_place.sql` (the `eligible` CTE filter and its new comment). The contract said "align the phrasing and say which"; the Developer aligned all three positions to `cdc_flag IS DISTINCT FROM 'D'`. In the expected-set position (the new audit) that is the strong reading, verbatim from the invariant. In the candidate position it is the weak one: a flag outside the anchored vocabulary {I, U, D, null} becomes a report, gets projected, feeds both sums, and the new converse audit goes silent on exactly the case its parallel_assumption names. That is a projection behavior change, not a rephrasing, and the L2 delta changed no selector. The header claims identity between a per-row filter and a whole-pair abstention that the same cycle's new audit distinguishes. Fix: revert the two candidate filters to the enumerated form; keep the new audit's whole-pair non-D test; say why the positions differ.

## Findings

1. **New audit: pass.** Whole-pair abstention (`GROUP BY pair HAVING BOOL_AND(cdc_flag IS DISTINCT FROM 'D')`), all four ownership values non-null on the joined trade row, both halves reported, reads confined.
2. **Candidate-filter alignment: the rejection.**
3. **Sum audits: pass.** Cardinality branch present; null-grouping catches null-bearing duplicate keys; union clean. Header says "Three checks" and lists two; the union dropped the diagnostic value columns.
4. **Updates-in-place:** clause 1 tolerance and clause 2 separation preserved; the hole.batch_identity note true; the eligible filter is the same defect in its weaker form, and the audit's own opening ("with cdc_flag I or U") now disagrees with its CTE.
5. **Manifest: pass.** Sha matches; note true; filed question kept.
6. **Cross-engine: a new divergence, this cycle's doing.** The sibling moved the opposite way (audits to the enumerated form, projection unchanged), so the two projections now disagree about which reports are candidates. On a report with an unanchored flag, native persists a row and stays silent on all 13 audits; SQLMesh persists no row and the converse audit fires. Invisible to compare on the fixture.
7. **Policy decided in SQL: one new item.** The treatment of a cdc_flag outside {I, U, D, null} is decided in SQL on both targets and by neither model text; it belongs in questions_for_authority.

Failure class: authorized phrasing alignment applied where the two phrasings are not equivalent, changing projection behavior and silencing the cycle's own new invariant.

## Routed

- CE proposal `ce.l3.holding-unanchored-cdc-flag` (filed as a runnable document): one holding report with cdc_flag 'X' for a fresh pair whose trade is fully pinned. Assertion as things stand: native persists and is silent; SQLMesh persists nothing and the converse audit fires.
- Question for authority, filed on both targets' manifests: is `trade_code_meanings.cdc_flag` a closed vocabulary, and is the latest_change candidate set "every non-D report" (hole.deletions' description) or "every I, U or historical report" (the invariant's parallel_assumption)?
- Coordinator note: the second contract sentence of mine in one day that presumed an equivalence the reviewer had to disprove ("add NOT NULL" was the first). Both are recorded in the session log as contract-authoring lessons.

Rejected artifacts: `holding_change.sql`, `audits/inv.holding_quantity_updates_in_place.sql`. Fix prescribed.
