-- inv.account_statement_has_content: every candidate-sourced statement of an
-- account carries a non-null status and a non-null tax_treatment; a versioned
-- statement without either is content-free and fails L1.statement-content.
-- Holds unconditionally for raw.customer_mgmt_action-sourced statements: NEW,
-- ADDACCT, and UPDACCT carry ca_tax_st directly; CLOSEACCT omits it, so
-- tax_treatment is carried forward from the account's preceding statement
-- under L1.omitted-facts-stand; status is entailed by the anchored
-- action_type meaning on every one of NEW, ADDACCT, UPDACCT, CLOSEACCT. Also
-- holds unconditionally for ce.account_changes-sourced statements, which carry
-- both status_id and tax_status_id directly on every row. Zero rows means the
-- invariant holds.

SELECT account_number, effective_from
FROM governed.account
WHERE status IS NULL OR tax_treatment IS NULL;
