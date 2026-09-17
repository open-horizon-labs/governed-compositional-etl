AUDIT (name inv.account_asof_has_unique_answer);

-- For any account_number and any moment T, exactly one statement is the latest one
-- effective at or before T: every statement must have a determinable effective_from and
-- no two statements of the same account may share one.
SELECT
  account_number,
  effective_from
FROM @this_model
WHERE effective_from IS NULL
UNION ALL
SELECT
  account_number,
  effective_from
FROM @this_model
GROUP BY account_number, effective_from
HAVING COUNT(*) > 1;
