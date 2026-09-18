AUDIT (name "inv.account_single_current");

-- For any account_number, at most one statement has is_current = true, always. If the
-- account's own record still stands (no statement of that account is a withdrawal) and its
-- owning customer still stands (the owning customer carries no withdrawal statement at all,
-- at any moment, per L1.owner-standing's extended second sentence), exactly one is current;
-- if either condition fails, none is current.
WITH owner_withdrawn AS (
  SELECT DISTINCT customer_number
  FROM governed.customer
  WHERE is_withdrawal
),
flags AS (
  SELECT
    a.account_number,
    SUM(CASE WHEN a.is_current THEN 1 ELSE 0 END) AS current_count,
    MAX(CASE WHEN a.is_withdrawal THEN 1 ELSE 0 END) AS own_withdrawn,
    MAX(CASE WHEN w.customer_number IS NOT NULL THEN 1 ELSE 0 END) AS owner_withdrawn
  FROM @this_model AS a
  LEFT JOIN owner_withdrawn AS w
    ON w.customer_number = a.owning_customer_number
  GROUP BY a.account_number
)
SELECT account_number
FROM flags
WHERE
  (own_withdrawn = 0 AND owner_withdrawn = 0 AND current_count <> 1)
  OR
  ((own_withdrawn = 1 OR owner_withdrawn = 1) AND current_count <> 0);
