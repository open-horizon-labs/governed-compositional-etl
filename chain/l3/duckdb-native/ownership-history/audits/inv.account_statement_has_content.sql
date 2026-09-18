-- inv.account_statement_has_content: every non-withdrawal (is_withdrawal =
-- false) candidate-sourced account statement carries a non-null status and a
-- non-null tax_treatment; a withdrawal statement (is_withdrawal = true)
-- carries neither, since it neither opens nor closes an account and asserts
-- no standing at all under L1.deletion-withdraws. is_withdrawal itself must
-- also be determinable (non-null): a statement whose withdrawal status is
-- unknown cannot be checked against either branch and is content-free for
-- the same reason. Zero rows means the invariant holds.

SELECT account_number, effective_from
FROM governed.account
WHERE is_withdrawal IS NULL
   OR (NOT is_withdrawal AND (status IS NULL OR tax_treatment IS NULL))
   OR (is_withdrawal AND (status IS NOT NULL OR tax_treatment IS NOT NULL));
