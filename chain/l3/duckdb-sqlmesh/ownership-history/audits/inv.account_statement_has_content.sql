AUDIT (name "inv.account_statement_has_content");

-- Every candidate-sourced statement of an account that is not itself a withdrawal
-- (is_withdrawal = false) carries a non-null status and a non-null tax_treatment; such a
-- non-withdrawal statement without either is content-free and fails L1.statement-content.
-- A withdrawal statement (is_withdrawal = true) carries neither status nor tax_treatment,
-- since it neither opens nor closes an account and asserts no standing at all, per
-- L1.deletion-withdraws -- so a withdrawal statement that carries either is the violation
-- in the other direction, not a silently-tolerated extra fact. An unresolvable
-- is_withdrawal is itself content-free: it cannot be classified into either branch, so it
-- is a violation rather than a silent pass.
SELECT
  account_number,
  effective_from
FROM @this_model
WHERE is_withdrawal IS NULL
   OR (NOT is_withdrawal AND (status IS NULL OR tax_treatment IS NULL))
   OR (is_withdrawal AND (status IS NOT NULL OR tax_treatment IS NOT NULL));
