-- inv.customer_statements_no_overlap: no two statements of the same
-- customer_number both apply at the same moment (no duplicate effective_from
-- within a customer_number). Zero rows means the invariant holds.

SELECT customer_number, effective_from, COUNT(*) AS n
FROM governed.customer
GROUP BY customer_number, effective_from
HAVING COUNT(*) > 1;
