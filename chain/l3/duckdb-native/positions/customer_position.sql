-- logical.customer_position: aggregate entity, one row per statement of a
-- customer, identified by (customer_number, customer_effective_from) as
-- pinned on every holding change's copied ownership reference. Source: this
-- job's own governed.holding_change (no raw or cross-job read).
--
-- derived_from:
--   logical.customer_position, logical.customer_position.customer_number,
--   logical.customer_position.customer_effective_from, logical.customer_position.net_quantity,
--   type.customer_position_key, type.customer_position_effective_from_key,
--   type.holding_quantity_change,
--   handoff.logical.holding_change.quantity_change->logical.customer_position.net_quantity
--
-- reads: governed.holding_change
--
-- Strategy: strategy_for_aggregate (CREATE OR REPLACE TABLE AS). Rebuilt in
-- full every cycle from governed.holding_change.
--
-- customer_number, customer_effective_from (computed_within_entity): equal to
-- the owning_customer_number and owning_customer_effective_from shared by
-- every logical.holding_change row grouped into this row; read off the group
-- itself via GROUP BY, once per group, never re-derived.
-- net_quantity (selector sum_of_deltas): SUM(quantity_change) across every
-- holding_change sharing this (customer_number, customer_effective_from) key.

CREATE OR REPLACE TABLE governed.customer_position AS
SELECT
    owning_customer_number AS customer_number,
    owning_customer_effective_from AS customer_effective_from,
    SUM(quantity_change) AS net_quantity
FROM governed.holding_change
GROUP BY owning_customer_number, owning_customer_effective_from;
