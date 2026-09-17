# Projection review 1: ownership-history on duckdb-sqlmesh (verdict: fail, one audit)

Reviewer: Opus judge with the L2 model as Sketch; ran check and run; verified against the fixture database.

Holds: kind FULL on both models, one SELECT each, no update path, the profile's custom-materialization workaround correctly absent (no incremental entity in this job); action filters exactly the model's sets; carry-forwards as last non-null earlier statement; is_current computed; reads confined to raw.customer_mgmt_action and ce.account_changes; ten audit predicates match their invariants; samples match the model for customer 238 and account 428.

Defect: `audits/inv.constructed_scenarios_labeled.sql` checks only that a present label is not blank; it checks neither clause of the invariant (constructed statements labeled; received statements unlabeled). Demonstrated vacuous: on a copy with provenance inverted on all five account statements the shipped predicate returns zero rows; a predicate joined to ce.account_changes on (account_id, action_at) returns all five. Second-order: inv.constructed_account_change_refers_to_known_account discriminates received from constructed by provenance nullness and so rested on the unchecked invariant.

Authorized correction: replace the predicate with the two-clause check against ce.account_changes (the entity's declared read); no other file changes.

Gate gap exposed: audits were not containment-checked. Fixed in chain_l3.py.

Representation choice named, not failed: status materialized in the anchored ACTV/INAC vocabulary for both entities; out-of-domain constructed status yields NULL and surfaces through the content invariant.
