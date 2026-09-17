MODEL (
  name governed.customer_position,
  kind FULL,
  dialect duckdb,
  audits (
    "inv.customer_position_not_negative",
    "inv.customer_position_key_matches_holding_change"
  ),
  depends_on (governed.holding_change)
);

-- logical.customer_position: one row per statement of a customer (customer_number,
-- customer_effective_from), aggregate, rebuilt FULL. customer_number/customer_effective_from
-- are computed_within_entity: read off the group's own owning_customer_number/
-- owning_customer_effective_from (already frozen on every logical.holding_change row per
-- sg.holding-attribution) the same way account_position reads its own keys.
-- net_quantity: handoff.logical.holding_change.quantity_change->
-- logical.customer_position.net_quantity, selector sum_of_deltas, grouped by the same keys.
SELECT
  owning_customer_number AS customer_number,
  owning_customer_effective_from AS customer_effective_from,
  SUM(quantity_change) AS net_quantity
FROM governed.holding_change
GROUP BY owning_customer_number, owning_customer_effective_from;
