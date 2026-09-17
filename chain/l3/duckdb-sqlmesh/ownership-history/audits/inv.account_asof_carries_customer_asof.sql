AUDIT (name "inv.account_asof_carries_customer_asof");

-- For any account_number and moment T, the account's as-of statement's
-- owning_customer_number, looked up as of the same moment T in the customer entity,
-- must yield the customer's as-of statement: owning_customer_number must be known, and a
-- customer statement effective at or before T must exist for it.
SELECT
  a.account_number,
  a.effective_from
FROM @this_model AS a
WHERE a.owning_customer_number IS NULL
   OR NOT EXISTS (
     SELECT 1
     FROM governed.customer AS c
     WHERE c.customer_number = a.owning_customer_number
       AND c.effective_from <= a.effective_from
   );
