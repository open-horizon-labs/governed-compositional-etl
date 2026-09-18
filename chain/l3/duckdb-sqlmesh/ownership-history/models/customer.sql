MODEL (
  name governed.customer,
  kind FULL,
  dialect duckdb,
  audits (
    "inv.customer_single_current",
    "inv.customer_statements_no_overlap",
    "inv.customer_asof_has_unique_answer",
    "inv.customer_statement_has_content",
    "inv.customer_status_matches_producing_source",
    "inv.customer_tier_matches_producing_source"
  )
);

-- logical.customer: one dated statement per customer, versioned, rebuilt FULL from the
-- complete raw.customer_mgmt_action change feed. Only NEW, UPDCUST, INACT rows carry a
-- customer subject (sources-v1.json action_type_meanings.subjects) and produce a customer
-- statement (handoff.raw.customer_mgmt_action.action_type->logical.customer.status).
--
-- logical.customer.is_withdrawal: computed_within_entity. raw.customer_mgmt_action's
-- action_type vocabulary (NEW, UPDCUST, INACT) names no withdrawal action at all, so every
-- statement this job currently produces has is_withdrawal = false. The only handoff that
-- could ever set it true is raw.customer_cdc.cdc_flag = 'D', which remains deferred under
-- L1.hole.change-effective-time and is not selected for this cycle; no handoff is invented
-- from it here.
WITH base AS (
  SELECT
    c_id AS customer_number,
    action_ts AS effective_from,
    FALSE AS is_withdrawal,
    -- handoff.raw.customer_mgmt_action.action_type->logical.customer.status
    -- status_from_action_meaning, using the anchored codes shared with ce.account_changes
    -- (sources-v1.json action_type_meanings.status_codes: ACTV/INAC)
    CASE action_type
      WHEN 'NEW' THEN 'ACTV'
      WHEN 'UPDCUST' THEN 'ACTV'
      WHEN 'INACT' THEN 'INAC'
    END AS status,
    -- handoff.raw.customer_mgmt_action.c_tier->logical.customer.tier
    -- INACT omits c_tier (sources-v1.json action_type_meanings.fields_present); the omission
    -- is resolved below via carried_forward_from_previous_statement, not read as a value here.
    CASE WHEN action_type IN ('NEW', 'UPDCUST') THEN c_tier ELSE NULL END AS tier_as_reported
  FROM raw.customer_mgmt_action
  WHERE action_type IN ('NEW', 'UPDCUST', 'INACT')
),
filled AS (
  SELECT
    customer_number,
    effective_from,
    is_withdrawal,
    status,
    -- logical.customer.tier: carried_forward_from_previous_statement (L1.omitted-facts-stand)
    -- when the producing action (INACT) omits c_tier. No candidate source produces a
    -- withdrawal statement, so the "carries no standing to carry forward" branch for
    -- is_withdrawal = true statements is not exercised here.
    LAST_VALUE(tier_as_reported IGNORE NULLS) OVER (
      PARTITION BY customer_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS tier
  FROM base
),
-- logical.customer.is_current's reversal-foreclosure branch: once a customer has any
-- withdrawal statement, no statement of that customer at or after the withdrawal's own
-- moment is ever current again (L1.hole.deletion-reversal, monotonic non-resuming reading).
withdrawal_bound AS (
  SELECT
    customer_number,
    MIN(effective_from) AS first_withdrawal_from
  FROM filled
  WHERE is_withdrawal
  GROUP BY customer_number
)
SELECT
  f.customer_number,
  f.effective_from,
  -- logical.customer.is_current: computed_within_entity.
  -- false when this statement's own is_withdrawal is true;
  -- false when a withdrawal statement of the same customer_number has an effective_from
  --   at or before this statement's effective_from (reversal-foreclosure, per
  --   L1.hole.deletion-reversal -- holds even for a later, ostensibly ordinary statement);
  -- otherwise true when no statement of the same customer_number has a later effective_from
  --   than this one, false when one does.
  CASE
    WHEN f.is_withdrawal THEN FALSE
    WHEN w.first_withdrawal_from IS NOT NULL AND w.first_withdrawal_from <= f.effective_from THEN FALSE
    ELSE f.effective_from = MAX(f.effective_from) OVER (PARTITION BY f.customer_number)
  END AS is_current,
  f.is_withdrawal,
  f.status,
  f.tier
FROM filled AS f
LEFT JOIN withdrawal_bound AS w
  ON w.customer_number = f.customer_number;
