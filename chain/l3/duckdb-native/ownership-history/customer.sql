-- logical.customer: versioned entity, one dated statement per customer.
-- Source: raw.customer_mgmt_action, the only selected source for this entity.
-- Rows with action_type NEW/UPDCUST/INACT produce a customer statement (per
-- chain/anchors/sources-v1.json action_type_meanings.subjects: only these three
-- codes have a customer subject).
--
-- derived_from:
--   logical.customer, logical.customer.customer_number, logical.customer.effective_from,
--   logical.customer.is_current, logical.customer.is_withdrawal, logical.customer.status,
--   logical.customer.tier,
--   type.customer_number, type.statement_effective_from, type.statement_is_current,
--   type.statement_is_withdrawal, type.customer_standing_status, type.customer_tier,
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
-- tier selector "carried_forward_from_previous_statement" (L2 cycle 2): INACT
-- omits c_tier (L1.omitted-facts-stand: the omitted fact stands as it last
-- stood), so tier equals the value carried by this customer's immediately
-- preceding statement, ordered by effective_from. INACT's anchored meaning
-- presupposes an existing customer (only NEW first records one), so a
-- preceding statement is guaranteed to exist.
--
-- is_withdrawal "computed_within_entity" (L2 cycle 3): false for every
-- statement produced by raw.customer_mgmt_action, whose action_type vocabulary
-- (NEW, UPDCUST, INACT) names no withdrawal action at all. The customer CDC
-- handoff that could set this true (raw.customer_cdc.cdc_flag = 'D') is
-- deferred under L1.hole.change-effective-time and is not read here; this
-- attribute is therefore always false for every statement this job currently
-- produces, which is the honest, unexercised state rather than a default.
--
-- is_current "computed_within_entity" (L2 cycle 3, amended): false when this
-- statement's own is_withdrawal is true; false when a withdrawal statement of
-- the same customer_number has an effective_from at or before this statement's
-- effective_from (reversal-foreclosure, L1.hole.deletion-reversal); otherwise
-- true when no statement of the same customer_number has a later effective_from
-- than this one, false when one does. With is_withdrawal always false today,
-- these withdrawal branches are unexercised, but the full rule is implemented
-- so a future undeferred CDC source needs no change to this logic.
--
-- status/tier: null exactly when is_withdrawal is true (never today), since a
-- withdrawal asserts no standing at all per L1.deletion-withdraws.
--
-- Carry-forward boundary: tier's carried_forward_from_previous_statement
-- derivation must not reach past a withdrawal. A withdrawal's own raw tier
-- is null (per the deferred raw.customer_cdc handoff's own note: "must
-- populate no value here"), and plain LAST_VALUE(... IGNORE NULLS) would
-- silently skip that null and carry the PRE-withdrawal tier across it to a
-- later statement. withdrawal_group (a running count of withdrawals up to
-- and including each row) partitions the carry-forward window so it never
-- looks earlier than the customer's own most recent withdrawal. Unreachable
-- today (is_withdrawal is hardcoded false for every row this file
-- produces), but wired so the derivation and inv.customer_statement_has_
-- content agree structurally rather than by coincidence once
-- raw.customer_cdc is undeferred.

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
        c_tier AS tier,
        -- raw.customer_mgmt_action's action_type vocabulary names no withdrawal
        -- action; the CDC source that could set this true is deferred.
        FALSE AS is_withdrawal
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'UPDCUST', 'INACT')
),
historical_grouped AS (
    SELECT
        *,
        -- running count of withdrawals up to and including this row: a
        -- withdrawal starts a new group (including itself), so carry-forward
        -- partitioned on this can never reach past it. See account.sql's
        -- "Carry-forward boundary" note; same reasoning, applied here to
        -- tier.
        SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) OVER (
            PARTITION BY customer_number ORDER BY effective_from
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS withdrawal_group
    FROM historical
),
carried AS (
    SELECT
        customer_number,
        effective_from,
        is_withdrawal,
        status AS status_raw,
        COALESCE(
            tier,
            LAST_VALUE(tier IGNORE NULLS) OVER (
                PARTITION BY customer_number, withdrawal_group ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS tier_carried
    FROM historical_grouped
),
withdrawals AS (
    SELECT customer_number, MIN(effective_from) AS first_withdrawal_from
    FROM carried
    WHERE is_withdrawal
    GROUP BY customer_number
)
SELECT
    c.customer_number,
    c.effective_from,
    CASE
        WHEN c.is_withdrawal THEN FALSE
        WHEN w.first_withdrawal_from IS NOT NULL AND w.first_withdrawal_from <= c.effective_from THEN FALSE
        WHEN c.effective_from = MAX(c.effective_from) OVER (PARTITION BY c.customer_number) THEN TRUE
        ELSE FALSE
    END AS is_current,
    c.is_withdrawal,
    CASE WHEN c.is_withdrawal THEN NULL ELSE c.status_raw END AS status,
    CASE WHEN c.is_withdrawal THEN NULL ELSE c.tier_carried END AS tier
FROM carried c
LEFT JOIN withdrawals w ON w.customer_number = c.customer_number;
