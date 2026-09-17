-- inv.account_statement_has_content: every statement of an account that is
-- sourced from a feed supplying its own standing facts carries a non-null
-- status and a non-null tax_treatment. Both selected sources
-- (raw.customer_mgmt_action, ce.account_changes) supply both directly or by
-- entailment, so no governed.account statement should be missing either.
-- Zero rows means the invariant holds.

SELECT account_number, effective_from
FROM governed.account
WHERE status IS NULL OR tax_treatment IS NULL;
