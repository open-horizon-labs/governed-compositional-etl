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

    def test_semantic_conversion_requires_named_authority(self):
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
        unauthorized = copy.deepcopy(mapping)
        unauthorized["authority"] = "raw-values-look-equal"
        with self.assertRaisesRegex(CONTRACTS.ContractError, "named business authority"):
            CONTRACTS.validate_semantic_mapping(unauthorized, types)

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


if __name__ == "__main__":
    unittest.main()
