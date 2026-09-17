AUDIT (name "inv.customer_statements_no_overlap");

-- No two statements of the same customer_number both apply at the same moment: each
-- (customer_number, effective_from) pair identifies at most one statement.
SELECT
  customer_number,
  effective_from
FROM @this_model
GROUP BY customer_number, effective_from
HAVING COUNT(*) > 1;
