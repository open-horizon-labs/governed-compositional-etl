AUDIT (name inv.account_statements_no_overlap);

-- No two statements of the same account_number both apply at the same moment: each
-- (account_number, effective_from) pair identifies at most one statement.
SELECT
  account_number,
  effective_from
FROM @this_model
GROUP BY account_number, effective_from
HAVING COUNT(*) > 1;
