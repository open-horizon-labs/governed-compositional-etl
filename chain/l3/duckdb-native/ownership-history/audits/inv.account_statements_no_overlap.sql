-- inv.account_statements_no_overlap: no two statements of the same
-- account_number both apply at the same moment (no duplicate effective_from
-- within an account_number). Zero rows means the invariant holds.

SELECT account_number, effective_from, COUNT(*) AS n
FROM governed.account
GROUP BY account_number, effective_from
HAVING COUNT(*) > 1;
