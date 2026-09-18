AUDIT (name "inv.withdrawal_never_reaches_account_status");

-- No logical.account.status or logical.account.tax_treatment value is ever populated by a
-- handoff sourced from a withdrawal report: a statement with is_withdrawal = true must
-- carry a null status and a null tax_treatment, since a withdrawal neither opens nor
-- closes an account, does not re-tax it, and creates no standing at all
-- (L1.deletion-withdraws). Neither candidate source (raw.customer_mgmt_action,
-- ce.account_changes) can produce a withdrawal statement, so this audit reports zero rows
-- on the fixture -- the correct empty result of an unexercised condition.
SELECT
  account_number,
  effective_from
FROM @this_model
WHERE is_withdrawal = TRUE
  AND (status IS NOT NULL OR tax_treatment IS NOT NULL);
