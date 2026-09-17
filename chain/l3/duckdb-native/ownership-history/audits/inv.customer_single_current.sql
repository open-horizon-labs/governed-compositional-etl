-- inv.customer_single_current: for any customer_number, at most one statement
-- has is_current = true, and exactly one if any statement of that customer
-- exists. Zero rows means the invariant holds.

SELECT customer_number
FROM governed.customer
GROUP BY customer_number
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1;
