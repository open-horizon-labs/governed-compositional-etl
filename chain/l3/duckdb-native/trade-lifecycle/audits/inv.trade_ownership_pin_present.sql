-- inv.trade_ownership_pin_present (L2 cycle 4, new): for any persisted
-- governed.trade row, owning_account_number, owning_account_effective_from,
-- owning_customer_number, and owning_customer_effective_from are each
-- non-null -- the full placement-moment ownership reference
-- L1.attribution-at-placement requires (which account, which of that
-- account's dated statements as of placed_at, and through that statement,
-- which customer), not merely a value present when convenient. trade.sql
-- LEFT JOINs the account and customer pins, so a trade whose account has no
-- governed.account statement at or before placed_at (or whose resolved
-- account has no governed.customer statement at or before placed_at) is
-- still persisted, with the unresolved reference columns null; that is the
-- violation this audit names. Zero rows means the invariant holds.

SELECT
    t.trade_number,
    t.owning_account_number,
    t.owning_account_effective_from,
    t.owning_customer_number,
    t.owning_customer_effective_from
FROM governed.trade AS t
WHERE t.owning_account_number IS NULL
   OR t.owning_account_effective_from IS NULL
   OR t.owning_customer_number IS NULL
   OR t.owning_customer_effective_from IS NULL;
