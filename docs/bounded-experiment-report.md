# Governed compositional ETL: bounded experiment report

## Research-sponsor decision

**Revise.** The materialized experiment shows promising compositional protection beyond native pipeline controls and independent stage-local CESS, but the sole valid run does not meet its preregistered quality threshold. Scope expansion is paused until a newly preregistered scorer correction and matched rerun.

The valid criteria are the honest work-unit criteria frozen before the valid run. The earlier pseudo-millisecond and wall-ratio criteria belong to invalid v1 and never govern this decision. The unit changed before the valid run because v1 fabricated milliseconds from deterministic operations. We do not apply or rehabilitate invalid v1 criteria; they would not turn the valid result into adoption because the valid quality gate fails independently.

Native and stage-local evidence retained both materially observed composition defects. Compositional evidence physically repaired both. The frozen scorer credits only one: its array comparison treats the governance-derived canonical descendant order as different from the frozen order despite equal members. This is a derived false negative, not a post-hoc score change. The valid run is never rescored.

Operator time is unavailable because the arms were scripted and no human timing was collected. Deterministic work units are a proxy count, not time. Model calls and tokens are measured zero. Monetary or normalized compute cost is unavailable; elapsed wall time is retained only as descriptive execution evidence.

## Canonical evidence

The JSON block below is the only quantitative and decision-bearing publication block. The machine decision pins its canonical hash and the complete report hash. The verifier independently recomputes every field from the valid traces, exact preregistration commit, frozen scorer/corpus behavior, replay evidence, and fresh projection.

<!-- BEGIN CANONICAL EVIDENCE -->
```json
{
  "arms": {
    "compositional_cess": {
      "active_repair_rate": 0.5,
      "authority_violations": 0,
      "compute_cost_available": false,
      "compute_cost_unavailable_reason": "No monetary or normalized resource-cost measurement was collected; elapsed wall time is descriptive only.",
      "escaped_composition_failures": 1,
      "heldout_regressions": 0,
      "localization_accuracy": 1.0,
      "model_calls": 0,
      "model_tokens": 0,
      "operator_time_available": false,
      "operator_time_unavailable_reason": "The arm used a scripted zero-model harness and collected no human operator timing.",
      "operator_work_units": 24,
      "wall_elapsed_seconds_descriptive": 23.608415417
    },
    "native": {
      "active_repair_rate": 0.25,
      "authority_violations": 0,
      "compute_cost_available": false,
      "compute_cost_unavailable_reason": "No monetary or normalized resource-cost measurement was collected; elapsed wall time is descriptive only.",
      "escaped_composition_failures": 2,
      "heldout_regressions": 1,
      "localization_accuracy": 0.4,
      "model_calls": 0,
      "model_tokens": 0,
      "operator_time_available": false,
      "operator_time_unavailable_reason": "The arm used a scripted zero-model harness and collected no human operator timing.",
      "operator_work_units": 19,
      "wall_elapsed_seconds_descriptive": 24.005366167
    },
    "stage_local_cess": {
      "active_repair_rate": 0.25,
      "authority_violations": 0,
      "compute_cost_available": false,
      "compute_cost_unavailable_reason": "No monetary or normalized resource-cost measurement was collected; elapsed wall time is descriptive only.",
      "escaped_composition_failures": 2,
      "heldout_regressions": 1,
      "localization_accuracy": 0.6,
      "model_calls": 0,
      "model_tokens": 0,
      "operator_time_available": false,
      "operator_time_unavailable_reason": "The arm used a scripted zero-model harness and collected no human operator timing.",
      "operator_work_units": 20,
      "wall_elapsed_seconds_descriptive": 21.933912917
    }
  },
  "chronology": {
    "invalid_v1_criteria": {
      "compositional_operator_pseudo_ms_multiple": 3.0,
      "governs_valid_run": false,
      "localized_replay_wall_multiple": 2.0,
      "reason_invalid": "V1 fabricated milliseconds from deterministic work units and used a non-executing harness.",
      "would_change_valid_decision_to_adopt": false
    },
    "unit_change_before_valid_run": "After invalidating fabricated v1 milliseconds, the valid preregistration uses explicit deterministic work units and treats measured wall time as descriptive only.",
    "valid_preregistration_commit": "e9aa5bb6e1dcaeb2d03af755a7073d2dbcbec608",
    "valid_preregistration_path": "experiments/preregistration-v2.2.json",
    "valid_preregistration_sha256": "7e22a6f1ac384c981b9be633cd6a552ff47235e2e8a9eecb4762286c2c4ccd5f",
    "valid_result_commit": "30109d75dc613a29682a37652c751ef474289608",
    "valid_thresholds_precede_result": true
  },
  "decision": {
    "bounded_decision": "revise",
    "cost_pass": true,
    "incremental_scored_composition_catches": 1,
    "operator_work_unit_multiple_vs_native": 1.263157894736842,
    "quality_pass": false,
    "valid_operator_work_unit_ceiling": 4.0,
    "valid_wall_time_role": "descriptive_only"
  },
  "fresh_projection": {
    "ce_archive_used": false,
    "excluded_context": [
      "oracle/",
      "counterexamples/archive/",
      "oracle/fixtures/held-out/",
      "oracle/submissions/held-out/"
    ],
    "manifest_sha256": "fc3baf16fdcff8fbd47ba4af9b132fc70d420ba6b7a2106b4a475c2cfa5cc9f3",
    "passed": true,
    "projection_sha256": "0669f058ba76e13763e930385896a774ce452348fdf735e6f57e58b739d90f08"
  },
  "limitations": {
    "corpus_private_case_count": 2,
    "corpus_visible_case_count": 5,
    "custody_tests_layer_availability_only": true,
    "generated_projection_diff_retained": false,
    "invalid_scored_attempts_excluded": [
      "v1",
      "v2_attempt_a",
      "v2.1",
      "v2.3"
    ],
    "issue4_executable_local_pass_test": "test_independent_local_checks_pass_while_edge_value_fails",
    "local_pass_contract_validator_rerun_inside_v2": false,
    "valid_file_internal_schema_label": "matched-experiment-result/v2.3",
    "valid_run": "v2.4"
  },
  "physical_vs_scored": {
    "edge": {
      "affected_descendant_members_equal": true,
      "affected_descendant_order_equal": false,
      "after": "2012-07-07T00:01:13",
      "before": "2012-07-07T00:02:34",
      "physically_repaired": true,
      "scored_pass": false
    },
    "path": {
      "after": 81,
      "before": 0,
      "physically_repaired": true,
      "scored_pass": true
    },
    "physical_composition_repairs": 2,
    "scored_composition_catches": 1,
    "scorer_false_negative_derived": true,
    "verification_gap": {
      "affected_descendant_members_equal": true,
      "affected_descendant_order_equal": false,
      "scored_pass": false
    }
  },
  "publication_gates": [
    "human_review_required",
    "no_compliant_tpc_di_benchmark_claim",
    "no_comparative_tpc_performance_claim",
    "claims_bounded_to_scripted_agents_and_selected_slice"
  ],
  "revalidation": {
    "full": {
      "audit_count": 6,
      "check_count": 5,
      "restaged_model_count": 6,
      "restaged_rows": 2155125,
      "semantic_recall": 1.0,
      "wall_elapsed_ms_descriptive": 1964.731
    },
    "localized": {
      "audit_count": 6,
      "check_count": 5,
      "restaged_model_count": 2,
      "restaged_rows": 781956,
      "reused_ancestor_count": 4,
      "semantic_precision": 1.0,
      "semantic_recall": 1.0,
      "wall_elapsed_ms_descriptive": 1840.893
    }
  },
  "thresholds": {
    "active_repair_rate_min": 0.8,
    "authority_violations_max": 0,
    "escaped_composition_failures_max": 0,
    "heldout_regressions_max": 0,
    "incremental_edge_or_composition_catches_min": 2,
    "localization_accuracy_min": 0.8,
    "revalidation_recall_min": 1.0
  }
}
```
<!-- END CANONICAL EVIDENCE -->

## Limitations and publication gates

The structured block records the bounded corpus, custody behavior, local-pass evidence source, omitted generated-projection diff, invalid-run exclusions, and internal schema-label wart. The evaluated DIGen copy pins core artifact hashes but was not personally acquired through the canonical registered TPC download. A human must acquire and compare the canonical package, accept and review its license, confirm obsolete-workload and fair-use language, and approve publication.

This is TPC-DI-derived research, not a compliant TPC-DI benchmark. It makes no comparative TPC or system-performance claim. Human review is required before external publication.
