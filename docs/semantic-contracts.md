# Semantic contracts and change authority

Issue #4 represents the bounded trade slice's meaning outside generated SQL. It does not define a universal semantic language. The contracts are small research artifacts whose main job is to make a wrong boundary, an unauthorized repair, or a silently filled hole mechanically visible.

## Contract set

The machine-readable schemas under `contracts/schema/` cover:

- source entities, grain, identifiers, structural fields, evidence, and holes;
- logical-model grain, attributes, governing rule IDs, verification, and disposition;
- semantic types with physical type, unit, sign convention, time role, history role, confidence, verification, and disposition;
- stage contracts with inputs, outputs, rule order, evidence, holes, and separate deterministic and Sketch-review checks;
- edge contracts with producers, consumer, mappings, history policy, rule order, evidence, and holes;
- repair-authority records with the active conceptual hat, allowed artifacts, forbidden adjacent policy, and conflict behavior.

The human-reviewable governing policy is [`sketches/trade-dim-v1.md`](../sketches/trade-dim-v1.md). Known rules and open holes are explicit and ordered there. JSON descriptors make those declarations testable; they do not replace review of the Sketch.

Run the retained verification and edge adjudication:

```sh
python3 -m pip install -r requirements-dev.txt
python3 scripts/contracts.py verify
python3 scripts/contracts.py adjudicate
```

The verifier checks every schema and instance with JSON Schema Draft 2020-12 before applying the cross-document semantic checks.

## Holes and authority

Every open hole names its question, owner hat, permitted resolution, and forbidden evidence. `raw_data`, `target_schema`, and `projection` are explicitly rejected as policy authority. A named TPC-DI rule or a repository-native approved decision may resolve a hole; a plausible raw pattern or convenient destination column may not. TPC authority must use the one canonical specification URL and a matching clause locator. Decision and counterexample authority must resolve to an existing tracked artifact under the exact allowed repository root; traversal, absolute, encoded, URL-like, and disguised paths are rejected.

Repair authority is scoped. The data-product-owner hat may authorize the TradeType reference repair at `sketch.stage.trade_type_reference` and the adjudicated lifecycle repair at `sketch.edge.trade_history_to_dim_trade`. Adjacent stage policy, downstream metrics, and physical projections remain forbidden. Domain-authority conflict stops for adjudication.

## Strong nominal distinction

`trade_record_timestamp` and `trade_creation_timestamp` are both physical `TIMESTAMP` values at one-second resolution. They are not substitutable semantic types. The former preserves `Trade.T_DTS`; the latter must be selected from status-qualified `TradeHistory.TH_DTS` under TPC-DI 1.1.0 clause 4.5.8.2. Treating physical equality as semantic compatibility recreates the seeded failure.

The issue #3 candidate therefore survives issue #4 adjudication as a bounded edge/composition failure:

- Trade and TradeHistory producer mappings pass independently.
- The DimTrade consumer faithfully copies the supplied typed handoff and passes its local time-order check.
- The handoff binds the Trade producer's `trade_recorded_at` field where the edge requires the TradeHistory producer's status-qualified field and supplies the wrong value; the edge contract fails.

The adjudicator resolves every evidence binding through its referenced producer contract and checks the edge target against the consumer's semantic-type-bearing input contract. Evidence cannot declare its own semantic type. The identity join is also executable: every history observation in a checked lifecycle must carry the same `trade_id` as its Trade row; missing, foreign, or mixed identities are rejected.

The same stage-binding validator checks every local contract before adjudication. Raw inputs must resolve uniquely to the source descriptor with the same nominal type; each output source must resolve uniquely to an input or declared intermediate; every stage copy preserves exact semantic type. No stage in this slice has conversion authority. The lifecycle edge is the sole semantic conversion surface and accepts only `tpc-di-1.1.0-4.5.8.2-create-close`, whose repair record allows only `sketch.edge.trade_history_to_dim_trade` and forbids adjacent stage Sketches.

This result retires the edge-versus-local risk only for this historical case. Incremental lifecycle composition remains an explicit hole.

## Projections

`contracts/artifact-classification-v1.json` classifies SQLMesh models, SQLGlot ASTs, generated SQL, and DuckDB tables as projections with no policy authority. Successful execution cannot promote them. Repair means changing an authorized governing Sketch and regenerating or rebuilding projections.

The complete accepted-counterexample archive, curated regression set, deterministic gates, and Sketch review remain separate even after executable projections are introduced in issue #5.
