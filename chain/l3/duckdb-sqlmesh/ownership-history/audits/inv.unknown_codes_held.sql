AUDIT (name "inv.unknown_codes_held");

-- L1.unknown-codes: a raw.customer_mgmt_action row whose action_type is outside the six
-- anchored codes (sources-v1.json action_type_meanings: NEW, ADDACCT, UPDACCT, UPDCUST,
-- CLOSEACCT, INACT) is held for review, never interpreted, defaulted, or dropped. This audit
-- names the held record and its code; both models already exclude such rows from every
-- derived customer or account statement via their WHERE clauses (no ELSE branch, no default),
-- so this audit reports the row directly against the source rather than against @this_model.
-- ce.account_changes is not checked here: it carries no anchored vocabulary of its own for
-- this job (the model files a question about that field), so it is left to the group's gap.
SELECT
  action_ts,
  c_id,
  action_type
FROM raw.customer_mgmt_action
WHERE action_type IS NULL
   OR action_type NOT IN ('NEW', 'ADDACCT', 'UPDACCT', 'UPDCUST', 'CLOSEACCT', 'INACT');
