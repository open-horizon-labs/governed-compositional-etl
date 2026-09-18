-- inv.withdrawal_never_reaches_account_status: no logical.account.status or
-- logical.account.tax_treatment value is ever populated by a handoff sourced
-- from a withdrawal report. Checkable form of L1.deletion-withdraws' "it
-- neither opens nor closes an account" and "creates nothing". Since
-- governed.account already nulls status and tax_treatment exactly when
-- is_withdrawal is true (see account.sql), this audit is the direct,
-- non-circular restatement of that requirement over the persisted table:
-- no withdrawal-flagged statement may carry either value. Zero rows means
-- the invariant holds.

SELECT account_number, effective_from
FROM governed.account
WHERE is_withdrawal
  AND (status IS NOT NULL OR tax_treatment IS NOT NULL);
