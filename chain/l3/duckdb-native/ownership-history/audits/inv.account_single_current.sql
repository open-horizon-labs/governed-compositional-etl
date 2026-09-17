-- inv.account_single_current: for any account_number, at most one statement
-- has is_current = true, and exactly one if any statement of that account
-- exists. Zero rows means the invariant holds.

SELECT account_number
FROM governed.account
GROUP BY account_number
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1;
