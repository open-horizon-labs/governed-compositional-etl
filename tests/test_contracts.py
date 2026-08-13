import copy
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contracts", ROOT / "scripts/contracts.py")
CONTRACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CONTRACTS)


class GovernedContractTests(unittest.TestCase):
    def test_complete_bundle_reproduces_edge_adjudication(self):
        result = CONTRACTS.validate_bundle()
        self.assertEqual(result["schemas_verified"], 6)
        self.assertEqual(result["contracts_verified"], 7)
        self.assertEqual(result["repair_authorities_verified"], 2)
        self.assertEqual(result["projection_classes_verified"], 4)
        self.assertGreaterEqual(result["holes_open"], 1)
        self.assertEqual(
            result["adjudication"],
            {
                "allowed_artifacts": ["sketch.edge.trade_history_to_dim_trade"],
                "failure_class": "edge_composition",
                "location": "edge.trade_history_to_dim_trade.create_close_time",
                "status": "adjudicated",
            },
        )

    def test_draft_2020_12_schemas_reject_missing_nested_contract_fields(self):
        schemas = CONTRACTS.validate_schema_files()
        stage = CONTRACTS.load_json(ROOT / "contracts/stages/trade-v1.json")
        missing_semantic_type = copy.deepcopy(stage)
        del missing_semantic_type["output"]["fields"][0]["semantic_type"]
        with self.assertRaisesRegex(CONTRACTS.ContractError, "semantic_type.*required"):
            CONTRACTS.validate_instance(
                schemas["stage-contract-v1.schema.json"],
                missing_semantic_type,
                "adversarial stage",
            )

        missing_input_semantic_type = copy.deepcopy(stage)
        del missing_input_semantic_type["input"]["fields"][0]["semantic_type"]
        with self.assertRaisesRegex(CONTRACTS.ContractError, "semantic_type.*required"):
            CONTRACTS.validate_instance(
                schemas["stage-contract-v1.schema.json"],
                missing_input_semantic_type,
                "adversarial stage input",
            )

        speculative_conversion = copy.deepcopy(stage)
        speculative_conversion["output"]["fields"][0]["conversion_rule"] = (
            "trade.speculative-conversion"
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "not allowed"):
            CONTRACTS.validate_instance(
                schemas["stage-contract-v1.schema.json"],
                speculative_conversion,
                "adversarial stage conversion",
            )

        authority = CONTRACTS.load_json(
            ROOT / "contracts/repair-authority/trade-lifecycle-edge-v1.json"
        )
        missing_conflict_behavior = copy.deepcopy(authority)
        del missing_conflict_behavior["conflict_behavior"]["raw_or_schema_inference"]
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "raw_or_schema_inference.*required"
        ):
            CONTRACTS.validate_instance(
                schemas["repair-authority-v1.schema.json"],
                missing_conflict_behavior,
                "adversarial authority",
            )

    def test_governing_sketch_is_ordered_incomplete_and_names_every_open_hole(self):
        sketch = (ROOT / "sketches/trade-dim-v1.md").read_text(encoding="utf-8")
        self.assertIn("status: incomplete", sketch)
        positions = [sketch.index(f"{number}. **") for number in range(1, 9)]
        self.assertEqual(positions, sorted(positions))

        descriptors = [
            CONTRACTS.load_json(ROOT / "contracts/sources/tpcdi-trade-source-v1.json"),
            CONTRACTS.load_json(ROOT / "contracts/logical-models/dim-trade-v1.json"),
            *[
                CONTRACTS.load_json(path)
                for path in sorted((ROOT / "contracts/stages").glob("*.json"))
            ],
            CONTRACTS.load_json(
                ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
            ),
        ]
        hole_ids = {
            hole["id"]
            for descriptor in descriptors
            for hole in descriptor.get("holes", [])
        }
        self.assertTrue(hole_ids)
        for hole_id in hole_ids:
            with self.subTest(hole_id=hole_id):
                self.assertIn(f"`{hole_id}`", sketch)

    def test_independent_local_checks_pass_while_edge_value_fails(self):
        case = CONTRACTS.load_json(
            ROOT / "evidence/issue-4/candidate-edge-check-v1.json"
        )
        trade = CONTRACTS.load_json(ROOT / "contracts/stages/trade-v1.json")
        history = CONTRACTS.load_json(
            ROOT / "contracts/stages/trade-history-v1.json"
        )
        consumer = CONTRACTS.load_json(
            ROOT / "contracts/stages/dim-trade-consumer-v1.json"
        )
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )

        self.assertEqual(
            CONTRACTS.apply_stage_mapping(trade, case["raw_trade"]),
            case["trade_stage_output"],
        )
        self.assertEqual(
            [CONTRACTS.apply_stage_mapping(history, row) for row in case["raw_history"]],
            case["history_stage_output"],
        )
        self.assertTrue(
            CONTRACTS.validate_consumer(
                consumer, case["consumer_input"], case["consumer_output"]
            )
        )
        self.assertNotEqual(
            CONTRACTS.expected_edge_handoff(
                edge, case["trade_stage_output"], case["history_stage_output"]
            ),
            case["consumer_input"],
        )

    def test_evidence_cannot_declare_its_own_semantic_type(self):
        case = CONTRACTS.load_json(
            ROOT / "evidence/issue-4/candidate-edge-check-v1.json"
        )
        stages = {
            contract["contract_id"]: contract
            for contract in [
                CONTRACTS.load_json(path)
                for path in sorted((ROOT / "contracts/stages").glob("*.json"))
            ]
        }
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}

        falsified = copy.deepcopy(case)
        falsified["handoff_bindings"]["created_at"]["source_semantic_type"] = (
            "trade_creation_timestamp"
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "evidence handoff binding"):
            CONTRACTS.adjudicate_candidate(stages, edge, types, falsified)

    def test_cross_document_binding_rejects_incompatible_producer_output(self):
        stages = {
            contract["contract_id"]: contract
            for contract in [
                CONTRACTS.load_json(path)
                for path in sorted((ROOT / "contracts/stages").glob("*.json"))
            ]
        }
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}
        incompatible = copy.deepcopy(stages)
        history = incompatible["stage.trade_history.v1"]
        next(
            field
            for field in history["output"]["fields"]
            if field["name"] == "status_updated_at"
        )["semantic_type"] = "trade_record_timestamp"
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "match the referenced producer contract"
        ):
            CONTRACTS.validate_edge_bindings(incompatible, edge, types)

        incompatible_consumer = copy.deepcopy(stages)
        consumer = incompatible_consumer["stage.dim_trade_consumer.v1"]
        next(
            field
            for field in consumer["input"]["fields"]
            if field["name"] == "created_at"
        )["semantic_type"] = "trade_record_timestamp"
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "match the consumer input contract"
        ):
            CONTRACTS.validate_edge_bindings(incompatible_consumer, edge, types)

    def test_generic_stage_bindings_reject_semantic_and_source_mutations(self):
        source = CONTRACTS.load_json(
            ROOT / "contracts/sources/tpcdi-trade-source-v1.json"
        )
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}
        consumer = CONTRACTS.load_json(
            ROOT / "contracts/stages/dim-trade-consumer-v1.json"
        )
        trade = CONTRACTS.load_json(ROOT / "contracts/stages/trade-v1.json")

        wrong_consumer_output = copy.deepcopy(consumer)
        next(
            field
            for field in wrong_consumer_output["output"]["fields"]
            if field["name"] == "created_at"
        )["semantic_type"] = "trade_record_timestamp"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "preserve exact"):
            CONTRACTS.validate_stage_bindings(
                wrong_consumer_output, source, types
            )

        wrong_trade_input = copy.deepcopy(trade)
        next(
            field
            for field in wrong_trade_input["input"]["fields"]
            if field["name"] == "t_dts"
        )["semantic_type"] = "status_update_timestamp"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "source descriptor"):
            CONTRACTS.validate_stage_bindings(wrong_trade_input, source, types)

        ambiguous_raw_source = copy.deepcopy(source)
        raw_trade = next(
            entity
            for entity in ambiguous_raw_source["entities"]
            if entity["name"] == "raw.trade"
        )
        raw_trade["fields"].append(copy.deepcopy(raw_trade["fields"][1]))
        with self.assertRaisesRegex(CONTRACTS.ContractError, "resolve uniquely"):
            CONTRACTS.validate_stage_bindings(trade, ambiguous_raw_source, types)

        missing_source = copy.deepcopy(consumer)
        next(
            field
            for field in missing_source["output"]["fields"]
            if field["name"] == "created_at"
        )["source"] = "missing_created_at"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "resolve uniquely"):
            CONTRACTS.validate_stage_bindings(missing_source, source, types)

        ambiguous_source = copy.deepcopy(consumer)
        ambiguous_source["input"]["fields"].append(
            {"name": "created_at", "semantic_type": "trade_record_timestamp"}
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "resolve uniquely"):
            CONTRACTS.validate_stage_bindings(ambiguous_source, source, types)

        forbidden_conversion_rule = copy.deepcopy(consumer)
        converted = next(
            field
            for field in forbidden_conversion_rule["output"]["fields"]
            if field["name"] == "created_at"
        )
        converted["semantic_type"] = "trade_record_timestamp"
        converted["conversion_rule"] = "dim-trade.unauthorized-conversion"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "does not permit"):
            CONTRACTS.validate_stage_bindings(
                forbidden_conversion_rule, source, types
            )

    def test_adjudication_runs_generic_stage_binding_validation(self):
        stages = {
            contract["contract_id"]: contract
            for contract in [
                CONTRACTS.load_json(path)
                for path in sorted((ROOT / "contracts/stages").glob("*.json"))
            ]
        }
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}
        mutated = copy.deepcopy(stages)
        consumer = mutated["stage.dim_trade_consumer.v1"]
        next(
            field
            for field in consumer["output"]["fields"]
            if field["name"] == "created_at"
        )["semantic_type"] = "trade_record_timestamp"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "preserve exact"):
            CONTRACTS.adjudicate_candidate(mutated, edge, types)

    def test_edge_identity_rejects_foreign_mixed_and_missing_trade_ids(self):
        case = CONTRACTS.load_json(
            ROOT / "evidence/issue-4/candidate-edge-check-v1.json"
        )
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )
        mixed = copy.deepcopy(case["history_stage_output"])
        mixed.append(
            {
                "status_id": "SBMT",
                "status_updated_at": "2012-07-07T00:01:14",
                "trade_id": 99,
            }
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "foreign, or mixed"):
            CONTRACTS.expected_edge_handoff(edge, case["trade_stage_output"], mixed)

        foreign = copy.deepcopy(case["history_stage_output"])
        for row in foreign:
            row["trade_id"] = 99
        with self.assertRaisesRegex(CONTRACTS.ContractError, "foreign, or mixed"):
            CONTRACTS.expected_edge_handoff(edge, case["trade_stage_output"], foreign)

        missing = copy.deepcopy(case["trade_stage_output"])
        del missing["trade_id"]
        with self.assertRaisesRegex(CONTRACTS.ContractError, "missing.*identity"):
            CONTRACTS.expected_edge_handoff(edge, missing, case["history_stage_output"])

    def test_physical_timestamp_equality_does_not_imply_semantic_compatibility(self):
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}
        actual = types["trade_record_timestamp"]
        required = types["trade_creation_timestamp"]
        self.assertEqual(actual["physical_type"], required["physical_type"])
        self.assertEqual(actual["unit"], required["unit"])
        self.assertFalse(
            CONTRACTS.semantic_type_compatible(
                "trade_record_timestamp", "trade_creation_timestamp"
            )
        )

    def test_raw_target_and_projection_cannot_fill_a_hole(self):
        for kind in ("raw_data", "target_schema", "projection"):
            authority = {
                "kind": kind,
                "id": f"forbidden-{kind}",
                "source": kind,
                "locator": "structurally plausible value",
            }
            with self.subTest(kind=kind), self.assertRaisesRegex(
                CONTRACTS.ContractError, "cannot fill policy holes"
            ):
                CONTRACTS.require_policy_authority(authority)

        source = CONTRACTS.load_json(
            ROOT / "contracts/sources/tpcdi-trade-source-v1.json"
        )
        hole = source["holes"][0]
        CONTRACTS.validate_hole(hole)
        silently_filled = copy.deepcopy(hole)
        silently_filled["status"] = "resolved"
        silently_filled["resolution"] = "target column exists"
        with self.assertRaises(CONTRACTS.ContractError):
            CONTRACTS.validate_hole(silently_filled)

    def test_edge_conversion_requires_exact_scoped_authority_and_edge_only_repair(self):
        registry = CONTRACTS.load_json(
            ROOT / "contracts/semantic-types/trade-types-v1.json"
        )
        types = {item["id"]: item for item in registry["types"]}
        edge = CONTRACTS.load_json(
            ROOT / "contracts/edges/trade-history-to-dim-trade-v1.json"
        )
        mapping = next(
            item for item in edge["mappings"] if item["to"].endswith("created_at")
        )
        CONTRACTS.validate_semantic_mapping(mapping, types)
        for authority in (
            "tpc-di-1.1.0-2.2.2.17",
            "tpc-di-1.1.0-4.5.8.2",
            "tpc-di-1.1.0-9.9.9",
        ):
            unauthorized = copy.deepcopy(mapping)
            unauthorized["authority"] = authority
            with self.subTest(authority=authority), self.assertRaisesRegex(
                CONTRACTS.ContractError, "exact vetted scoped authority"
            ):
                CONTRACTS.validate_semantic_mapping(unauthorized, types)

        repair = CONTRACTS.load_json(
            ROOT / "contracts/repair-authority/trade-lifecycle-edge-v1.json"
        )
        stage_allowed = copy.deepcopy(repair)
        stage_allowed["forbidden_adjacent_policy"].remove("sketch.stage.trade")
        stage_allowed["allowed_artifacts"].append("sketch.stage.trade")
        with self.assertRaisesRegex(CONTRACTS.ContractError, "only its edge Sketch"):
            CONTRACTS.validate_semantic_mapping(mapping, types, stage_allowed)

        missing_stage_prohibition = copy.deepcopy(repair)
        missing_stage_prohibition["forbidden_adjacent_policy"].remove(
            "sketch.stage.trade"
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "forbid adjacent stage"):
            CONTRACTS.validate_semantic_mapping(
                mapping, types, missing_stage_prohibition
            )

        active_forbidden = copy.deepcopy(repair)
        active_forbidden["forbidden_adjacent_policy"].append(
            "sketch.edge.trade_history_to_dim_trade"
        )
        with self.assertRaisesRegex(CONTRACTS.ContractError, "non-overlapping"):
            CONTRACTS.validate_semantic_mapping(mapping, types, active_forbidden)

    def test_projection_cannot_promote_itself_to_policy_authority(self):
        classification = CONTRACTS.load_json(
            ROOT / "contracts/artifact-classification-v1.json"
        )
        CONTRACTS.validate_projection_classification(classification)
        promoted = copy.deepcopy(classification)
        sql = next(item for item in promoted["artifacts"] if item["id"] == "generated_sql")
        sql["policy_authority"] = True
        with self.assertRaisesRegex(CONTRACTS.ContractError, "non-governing projection"):
            CONTRACTS.validate_projection_classification(promoted)

    def test_repair_authority_rejects_overlap_and_weakened_conflict_behavior(self):
        record = CONTRACTS.load_json(
            ROOT / "contracts/repair-authority/trade-lifecycle-edge-v1.json"
        )
        CONTRACTS.validate_repair_authority(record)

        overlap = copy.deepcopy(record)
        overlap["forbidden_adjacent_policy"].append(overlap["allowed_artifacts"][0])
        with self.assertRaisesRegex(CONTRACTS.ContractError, "non-overlapping"):
            CONTRACTS.validate_repair_authority(overlap)

        weakened = copy.deepcopy(record)
        weakened["conflict_behavior"]["projection_edit"] = "allow_hotfix"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "incomplete"):
            CONTRACTS.validate_repair_authority(weakened)

        for forbidden_kind in ("raw_data", "target_schema", "projection"):
            structural_basis = copy.deepcopy(record)
            structural_basis["active_authority"]["basis"] = [
                {
                    "id": f"forbidden-{forbidden_kind}",
                    "kind": forbidden_kind,
                    "locator": "plausible structure",
                    "source": forbidden_kind,
                }
            ]
            with self.subTest(forbidden_kind=forbidden_kind), self.assertRaisesRegex(
                CONTRACTS.ContractError, "cannot fill policy holes"
            ):
                CONTRACTS.validate_repair_authority(structural_basis)

        disguised_projection = copy.deepcopy(record)
        disguised_projection["active_authority"]["basis"] = [
            {
                "id": "tpc-di-1.1.0-fake",
                "kind": "tpc_di_rule",
                "locator": "generated expression",
                "source": "generated_sql.dim_trade",
            }
        ]
        with self.assertRaisesRegex(CONTRACTS.ContractError, "canonical specification"):
            CONTRACTS.validate_repair_authority(disguised_projection)

    def test_authority_references_reject_prefix_traversal_and_encoding_bypasses(self):
        decision_template = {
            "id": "decision",
            "kind": "approved_decision",
            "locator": "Decision",
            "source": ".oh/metis/issue-4-candidate-edge-adjudication.md",
        }
        invalid_decisions = [
            ".oh/metis/../AGENTS.md",
            "/.oh/metis/issue-4-candidate-edge-adjudication.md",
            "file://.oh/metis/issue-4-candidate-edge-adjudication.md",
            ".oh/metis/%2e%2e/AGENTS.md",
            ".oh%2fmetis%2fissue-4-candidate-edge-adjudication.md",
            ".oh\\metis\\issue-4-candidate-edge-adjudication.md",
        ]
        for source in invalid_decisions:
            authority = copy.deepcopy(decision_template)
            authority["source"] = source
            with self.subTest(source=source), self.assertRaises(
                CONTRACTS.ContractError
            ):
                CONTRACTS.require_policy_authority(authority)

        counterexample = {
            "id": "ce-bypass",
            "kind": "approved_counterexample",
            "locator": "approved clause",
            "source": "counterexamples/archive/../fixture.json",
        }
        with self.assertRaises(CONTRACTS.ContractError):
            CONTRACTS.require_policy_authority(counterexample)
        counterexample["source"] = "counterexamples/archive/not-approved.json"
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "existing tracked artifact"
        ):
            CONTRACTS.require_policy_authority(counterexample)

        tpc = {
            "id": "tpc-di-1.1.0-4.5.8.2",
            "kind": "tpc_di_rule",
            "locator": "Clause 4.5.8.2",
            "source": "https://www.tpc.org.evil.example/tpc-di_v1.1.0.pdf",
        }
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "canonical specification"
        ):
            CONTRACTS.require_policy_authority(tpc)
        for suffix in ("?download=1", "#clause", "%3ftampered"):
            encoded = copy.deepcopy(tpc)
            encoded["source"] = CONTRACTS.TPC_SPEC_URL + suffix
            with self.subTest(suffix=suffix), self.assertRaisesRegex(
                CONTRACTS.ContractError, "canonical specification"
            ):
                CONTRACTS.require_policy_authority(encoded)
        disguised_locator = copy.deepcopy(tpc)
        disguised_locator["source"] = CONTRACTS.TPC_SPEC_URL
        disguised_locator["locator"] = "Clause 4.5.8.2 https://evil.example"
        with self.assertRaisesRegex(
            CONTRACTS.ContractError, "canonical specification"
        ):
            CONTRACTS.require_policy_authority(disguised_locator)

    def test_rule_order_exactly_covers_rules_and_excludes_verification(self):
        stage = CONTRACTS.load_json(ROOT / "contracts/stages/trade-v1.json")
        CONTRACTS.validate_rule_order(stage, stage["contract_id"])
        phantom = copy.deepcopy(stage)
        phantom["rule_order"].append("trade.local-verification")
        with self.assertRaisesRegex(CONTRACTS.ContractError, "exactly cover"):
            CONTRACTS.validate_rule_order(phantom, phantom["contract_id"])

        missing = copy.deepcopy(stage)
        missing["rule_order"] = []
        with self.assertRaisesRegex(CONTRACTS.ContractError, "exactly cover"):
            CONTRACTS.validate_rule_order(missing, missing["contract_id"])


if __name__ == "__main__":
    unittest.main()
