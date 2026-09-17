AUDIT (name inv.customer_single_current);

-- For any customer_number, at most one statement has is_current = true, and if any
-- statement of that customer exists, exactly one does. A group is a violation when its
-- count of is_current = true statements is not exactly one.
SELECT
  customer_number
FROM @this_model
GROUP BY customer_number
HAVING SUM(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1;
