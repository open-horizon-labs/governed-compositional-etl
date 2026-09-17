AUDIT (name "inv.trade_ownership_pin_present");

-- For any persisted governed.trade row, owning_account_number, owning_account_effective_from,
-- owning_customer_number, and owning_customer_effective_from are each non-null: the account
-- and, through it, the customer statement in effect at placed_at. A row carrying any of the
-- four as null is a trade whose pin did not resolve, which this invariant names rather than
-- lets pass silently.
SELECT
  m.trade_number
FROM @this_model AS m
WHERE m.owning_account_number IS NULL
   OR m.owning_account_effective_from IS NULL
   OR m.owning_customer_number IS NULL
   OR m.owning_customer_effective_from IS NULL;
