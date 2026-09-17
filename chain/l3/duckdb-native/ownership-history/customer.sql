-- logical.customer: versioned entity, one dated statement per customer.
-- Source: raw.customer_mgmt_action, the only selected source for this entity.
-- Rows with action_type NEW/UPDCUST/INACT produce a customer statement (per
-- chain/anchors/sources-v1.json action_type_meanings.subjects: only these three
-- codes have a customer subject).
--
-- derived_from:
--   logical.customer, logical.customer.customer_number, logical.customer.effective_from,
--   logical.customer.is_current, logical.customer.status, logical.customer.tier,
--   type.customer_number, type.statement_effective_from, type.statement_is_current,
--   type.customer_standing_status, type.customer_tier,
--   handoff.raw.customer_mgmt_action.c_id->logical.customer.customer_number,
--   handoff.raw.customer_mgmt_action.action_ts->logical.customer.effective_from,
--   handoff.raw.customer_mgmt_action.action_type->logical.customer.status,
--   handoff.raw.customer_mgmt_action.c_tier->logical.customer.tier
--
-- reads: raw.customer_mgmt_action
--
-- Strategy: strategy_for_versioned (CREATE OR REPLACE TABLE AS from the complete
-- change feed). No updates in place; per_statement values are never updated.
--
-- status selector "status_from_action_meaning": maps action_type to the anchored
-- status_codes exactly as chain/anchors/sources-v1.json states them
-- (NEW, UPDCUST -> ACTV; INACT -> INAC).
--
-- is_current selector "computed_within_entity": true when no statement of the
-- same customer_number has a later effective_from than this one.

CREATE OR REPLACE TABLE governed.customer AS
WITH historical AS (
    SELECT
        c_id AS customer_number,
        action_ts AS effective_from,
        CASE action_type
            WHEN 'NEW'    THEN 'ACTV'
            WHEN 'UPDCUST' THEN 'ACTV'
            WHEN 'INACT'  THEN 'INAC'
        END AS status,
        c_tier AS tier
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'UPDCUST', 'INACT')
)
SELECT
    customer_number,
    effective_from,
    (effective_from = MAX(effective_from) OVER (PARTITION BY customer_number)) AS is_current,
    status,
    tier
FROM historical;
