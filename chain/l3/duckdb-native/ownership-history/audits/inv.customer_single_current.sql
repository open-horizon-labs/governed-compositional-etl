-- inv.customer_single_current: for any customer_number, at most one statement
-- has is_current = true, always. If the record still stands (no statement of
-- that customer is a withdrawal), exactly one is current; if it does not
-- (any statement is a withdrawal, per the reversal-foreclosure reading of
-- L1.hole.deletion-reversal), none is current. Zero rows means the invariant
-- holds.

SELECT customer_number
FROM governed.customer
GROUP BY customer_number
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) > 1
    OR (
        SUM(CASE WHEN is_current THEN 1 ELSE 0 END) = 0
        AND SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) = 0
    );
