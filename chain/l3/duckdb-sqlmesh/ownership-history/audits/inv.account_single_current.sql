AUDIT (name inv.account_single_current);

-- For any account_number, at most one statement has is_current = true, and if any
-- statement of that account exists, exactly one does.
SELECT
  account_number
FROM @this_model
GROUP BY account_number
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1;
