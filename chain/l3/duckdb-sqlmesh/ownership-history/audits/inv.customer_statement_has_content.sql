AUDIT (name "inv.customer_statement_has_content");

-- Every candidate-sourced statement of a customer that is not itself a withdrawal
-- (is_withdrawal = false) carries a non-null status and a non-null tier; such a
-- non-withdrawal statement without either is content-free and fails L1.statement-content.
-- A withdrawal statement (is_withdrawal = true) carries neither status nor tier, since it
-- asserts no standing at all, per L1.deletion-withdraws -- so a withdrawal statement that
-- carries either is the violation in the other direction, not a silently-tolerated extra
-- fact. An unresolvable is_withdrawal is itself content-free: it cannot be classified into
-- either branch, so it is a violation rather than a silent pass.
SELECT
  customer_number,
  effective_from
FROM @this_model
WHERE is_withdrawal IS NULL
   OR (NOT is_withdrawal AND (status IS NULL OR tier IS NULL))
   OR (is_withdrawal AND (status IS NOT NULL OR tier IS NOT NULL));
