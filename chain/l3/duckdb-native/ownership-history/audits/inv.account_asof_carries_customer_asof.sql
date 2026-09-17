-- inv.account_asof_carries_customer_asof: for any account_number and moment T,
-- the account's as-of statement's owning_customer_number, looked up as of the
-- same moment T in the customer entity, must yield a customer as-of statement.
-- Using each account statement's own effective_from as a representative moment
-- T, every account statement must have a resolvable owning_customer_number and
-- a customer statement of that customer effective at or before the same
-- moment. Zero rows means the invariant holds.

SELECT a.account_number, a.effective_from
FROM governed.account a
WHERE a.owning_customer_number IS NULL
   OR NOT EXISTS (
        SELECT 1
        FROM governed.customer c
        WHERE c.customer_number = a.owning_customer_number
          AND c.effective_from <= a.effective_from
   );
