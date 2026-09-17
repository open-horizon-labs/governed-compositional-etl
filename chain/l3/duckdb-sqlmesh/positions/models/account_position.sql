MODEL (
  name governed.account_position,
  kind FULL,
  dialect duckdb,
  audits (
    "inv.account_position_not_negative",
    "inv.account_position_key_matches_holding_change",
    "inv.account_position_is_sum_of_changes"
  ),
  depends_on (governed.holding_change)
);

-- logical.account_position: one row per statement of an account (account_number,
-- account_effective_from), aggregate, rebuilt FULL. account_number/account_effective_from are
-- computed_within_entity: read off the group's own owning_account_number/
-- owning_account_effective_from (already frozen on every logical.holding_change row per
-- sg.holding-attribution) rather than handed off from a single source row, since a group is
-- exactly the set of holding_change rows sharing that value.
-- net_quantity: handoff.logical.holding_change.quantity_change->
-- logical.account_position.net_quantity, selector sum_of_deltas, grouped by the same keys.
SELECT
  owning_account_number AS account_number,
  owning_account_effective_from AS account_effective_from,
  SUM(quantity_change) AS net_quantity
FROM governed.holding_change
GROUP BY owning_account_number, owning_account_effective_from;
