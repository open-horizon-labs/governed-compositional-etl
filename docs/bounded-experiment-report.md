# Governed compositional ETL: bounded experiment report

## Decision

**Revise.** The selected slice shows materially promising protection beyond native pipeline controls and independent stage-local CESS, but it does not meet the frozen adoption threshold. The valid v2.4 scorer credits one of two composition catches and compositional active repair is 0.5. The method should be corrected and rerun under a new preregistration before expanding beyond this slice.

This decision was made under the research-sponsor hat. The numerical quality and cost rules were frozen in commit `e9aa5bb` before the valid v2.4 result commit `30109d7`. Earlier v1, v2 attempt A, v2.1, and v2.3 results are invalid failed-harness learning; v2.2 stopped at preflight. None contributes to the decision.

## Comparison with traditional and stage-local development

| Metric | Native SQLMesh/DuckDB | Stage-local CESS | Compositional CESS |
|---|---:|---:|---:|
| Localization accuracy | 0.4 | 0.6 | 1.0 |
| Active repair rate | 0.25 | 0.25 | 0.5 |
| Authority violations | 0 | 0 | 0 |
| Held-out regressions | 1 | 1 | 0 |
| Escaped scored composition failures | 2 | 2 | 1 |
| Deterministic operator work units | 19 | 20 | 24 |
| Model calls / tokens | 0 / 0 | 0 / 0 | 0 / 0 |
| Descriptive wall seconds | 24.005 | 21.934 | 23.608 |

Native and stage-local evidence remained inconclusive on both composition defects and retained the materialized wrong values. Compositional evidence physically repaired the edge timestamp from `00:02:34` to `00:01:13` and the path duration from `0` to `81`. That does **not** become two scored catches: the frozen scorer counted only the path repair because its affected-descendant array comparison was order-sensitive. The edge and verification-gap proposals contained the exact governed members in canonical order but not the frozen array order. Fixing that scorer requires a future preregistration; v2.4 is never rescored.

Missing pricing policy remained explicit and inconclusive in all arms. No arm inferred policy from raw data, schemas, or generated projection structure.

## Revalidation cost and safety

For the governed edge change, localized replay restaged 2 models and 781,956 rows, reused 4 verified ancestors, and ran 5 checks plus 6 audits. Full replay restaged all 6 models and 2,155,125 rows with the same 5 checks and 6 audits. Both had semantic recall 1.0; localized semantic precision was 1.0. The observed wall times—1,840.893 ms localized and 1,964.731 ms full—are descriptive single-host observations, not a speed or performance claim. Correct descendant coverage, not smaller replay, is the safety result.

The deterministic work count is an honest harness work unit, not human operator time. No human-time study or LLM comparison occurred. All arms used scripted deterministic policy with zero model calls and tokens.

## Evidence and regeneration

The independent envelope verifier recomputes frozen harness and corpus hashes, retained result and trace hashes, matched start-database hashes, actual localized/full replay records, attempt budgets, and the conditional materialization rule: resolved proposals change the injected output; inconclusive proposals retain it. Every resolved case retains a non-empty actual artifact diff within its frozen allowed surface; inconclusive cases retain no edit.

The fresh-projection check deletes and regenerates the disposable projection from the Sketch, anchors, contracts, and bounded compiler profile. Its manifest explicitly excludes the oracle, accepted-CE archive, held-out fixtures, and held-out submissions. The regenerated arms remain byte-equivalent at projection hash `0669f058…` and pass independent manifest verification. Generated SQL, SQLGlot ASTs, SQLMesh models, and DuckDB tables remain replaceable projections.

## Limitations and publication gates

- The arm policy is deterministic and scripted, with zero model use. This is not evidence about LLM repair performance.
- V2 records producer/consumer local passes for the edge, but the executable basis is the earlier issue #4 adjudication test; v2 did not independently rerun that contract validator inside every disposable case.
- The retained artifact diff covers the governed repair surface but omits the separately regenerated projection diff.
- Private custody tests whether the arm exposes the needed evidence layer and emits aggregates only; it is not a broad neighboring-data generalization test.
- The corpus has five visible cases and two private neighbors in one batch Trade slice. Statistical inference and external validity are unavailable.
- Multiple invalid harness iterations demonstrate that the evaluation machinery itself required correction. Only v2.4 counts.
- The valid v2.4 file retains the internal schema label `matched-experiment-result/v2.3`; the filename, chronology, nonce, envelope, and decision identify the valid attempt. Correcting that label after scoring would invalidate the envelope, so it remains unchanged.
- Timings are descriptive and cannot support comparative system or TPC performance claims.
- The evaluated DIGen copy pins three core artifact hashes in the issue #2 manifest, but it was not personally acquired through the canonical registered TPC download. A human must acquire that package, compare the pinned hashes, accept/review its license, confirm the obsolete workload status and fair-use wording, and approve external publication.

This work is TPC-DI-derived research, not a compliant TPC-DI benchmark. It makes no comparative TPC performance claim. Human review is required before external publication.
