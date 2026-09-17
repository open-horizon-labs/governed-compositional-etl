-- inv.unknown_codes_held: every raw.customer_mgmt_action row this job
-- consumes must carry an action_type named in
-- chain/anchors/sources-v1.json's action_type_meanings (NEW, ADDACCT,
-- UPDACCT, UPDCUST, CLOSEACCT, INACT). A row carrying any other value is
-- reported here, naming the row (c_id, action_ts) and its action_type, per
-- L1.unknown-codes: the code is held for review, never interpreted,
-- defaulted, or dropped. Zero rows means the invariant holds.
--
-- ce.account_changes is a labeled constructed scenario (see
-- inv.constructed_scenarios_labeled) whose status_id/tax_status_id carry no
-- anchored code vocabulary of their own; sg.unknown-codes' coverage_claim
-- restricts this invariant to raw.customer_mgmt_action.action_type, the one
-- coded field this job reads from a currently-projectable candidate source
-- against an anchored vocabulary.

SELECT
    c_id,
    action_ts,
    action_type
FROM raw.customer_mgmt_action
WHERE action_type IS NULL
   OR action_type NOT IN ('NEW', 'ADDACCT', 'UPDACCT', 'UPDCUST', 'CLOSEACCT', 'INACT');
