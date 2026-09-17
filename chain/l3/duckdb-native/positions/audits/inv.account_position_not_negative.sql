-- inv.account_position_not_negative: net_quantity, the sum of quantity_change
-- across every holding_change whose owning_account_number and
-- owning_account_effective_from equal this row's account_number and
-- account_effective_from, is never negative. A null net_quantity (which
-- should not occur, since SUM over a non-nullable column grouped by a
-- non-nullable key cannot itself be null) is treated as a violation rather
-- than silently passing an inequality test. Zero rows means the invariant
-- holds.

SELECT
    account_number,
    account_effective_from,
    net_quantity
FROM governed.account_position
WHERE net_quantity < 0
   OR net_quantity IS NULL;
