MODEL (
  name governed.customer,
  kind FULL,
  dialect duckdb,
  audits (
    "inv.customer_single_current",
    "inv.customer_statements_no_overlap",
    "inv.customer_asof_has_unique_answer",
    "inv.customer_statement_has_content"
  )
);

-- logical.customer: one dated statement per customer, versioned, rebuilt FULL from the
-- complete raw.customer_mgmt_action change feed. Only NEW, UPDCUST, INACT rows carry a
-- customer subject (sources-v1.json action_type_meanings.subjects) and produce a customer
-- statement (handoff.raw.customer_mgmt_action.action_type->logical.customer.status).
WITH base AS (
  SELECT
    c_id AS customer_number,
    action_ts AS effective_from,
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
    status,
    -- logical.customer.tier: carried_forward_from_previous_statement (L1.omitted-facts-stand)
    -- when the producing action (INACT) omits c_tier.
    LAST_VALUE(tier_as_reported IGNORE NULLS) OVER (
      PARTITION BY customer_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS tier
  FROM base
)
SELECT
  customer_number,
  effective_from,
  -- logical.customer.is_current: computed_within_entity, true when no statement of the same
  -- customer_number has a later effective_from than this one.
  effective_from = MAX(effective_from) OVER (PARTITION BY customer_number) AS is_current,
  status,
  tier
FROM filled;
