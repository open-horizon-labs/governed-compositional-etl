AUDIT (name inv.customer_asof_has_unique_answer);

-- For any customer_number and any moment T, exactly one statement is the latest one
-- effective at or before T. This holds exactly when every statement has a determinable
-- effective_from and no two statements of the same customer share one (the no-overlap
-- and ordering conditions L1.as-of's uniqueness depends on).
SELECT
  customer_number,
  effective_from
FROM @this_model
WHERE effective_from IS NULL
UNION ALL
SELECT
  customer_number,
  effective_from
FROM @this_model
GROUP BY customer_number, effective_from
HAVING COUNT(*) > 1;
