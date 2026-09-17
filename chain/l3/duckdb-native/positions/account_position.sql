-- logical.account_position: aggregate entity, one row per statement of an
-- account, identified by (account_number, account_effective_from) as pinned
-- on every holding change's copied ownership reference. Source: this job's
-- own governed.holding_change (no raw or cross-job read; the grouping keys
-- and summed quantity all come from the entity this job already projected).
--
-- derived_from:
--   logical.account_position, logical.account_position.account_number,
--   logical.account_position.account_effective_from, logical.account_position.net_quantity,
--   type.account_position_account_key, type.account_position_effective_from_key,
--   type.holding_quantity_change,
--   handoff.logical.holding_change.quantity_change->logical.account_position.net_quantity
--
-- reads: governed.holding_change
--
-- Strategy: strategy_for_aggregate (CREATE OR REPLACE TABLE AS). Rebuilt in
-- full every cycle from governed.holding_change.
--
-- account_number, account_effective_from (computed_within_entity): equal to
-- the owning_account_number and owning_account_effective_from shared by every
-- logical.holding_change row grouped into this row; read off the group itself
-- via GROUP BY, once per group, never re-derived.
-- net_quantity (selector sum_of_deltas): SUM(quantity_change) across every
-- holding_change sharing this (account_number, account_effective_from) key.

CREATE OR REPLACE TABLE governed.account_position AS
SELECT
    owning_account_number AS account_number,
    owning_account_effective_from AS account_effective_from,
    SUM(quantity_change) AS net_quantity
FROM governed.holding_change
GROUP BY owning_account_number, owning_account_effective_from;
