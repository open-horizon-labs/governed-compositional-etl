# Projection review 1: ownership-history on duckdb-native (verdict: pass, unconditional)

Reviewer: Opus judge with the L2 model as its Sketch; ran check and run read-only; verified carry-forwards against fixture inputs.

Holds: both entities rebuilt with CREATE OR REPLACE TABLE AS; no UPDATE, MERGE, INSERT, or DELETE anywhere; reads confined to raw.customer_mgmt_action and ce.account_changes; status mapped for exactly the six anchored codes with no ELSE; carry-forward as last non-null earlier statement over the combined feed; is_current as the literal rule; all 11 audits present with predicates matching their invariants; samples match the model for customer 238 and account 428; the INACT moment creates no account statements and the 2012 closure is not revised by the 2017 change, leaving both holes open.

Policy decided in SQL: none. Representation choices traceable to anchors: status encoded in the anchored ACTV/INAC vocabulary; the constructed-label audit also fails an empty string, grounded in the handoff's review trigger.

Flagged: the L2 -> L3 contract glossed as_of_event_time with effective_to, which this model does not declare (contract wording corrected); a constructed change legitimately becomes the account's current statement under the model as written, which is a model question for the business if unintended.
