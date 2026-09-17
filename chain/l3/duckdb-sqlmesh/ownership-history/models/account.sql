MODEL (
  name governed.account,
  kind FULL,
  dialect duckdb,
  audits (
    "inv.account_single_current",
    "inv.account_statements_no_overlap",
    "inv.account_asof_has_unique_answer",
    "inv.account_statement_has_content",
    "inv.constructed_scenarios_labeled",
    "inv.constructed_account_change_refers_to_known_account",
    "inv.account_asof_carries_customer_asof",
    "inv.account_status_matches_producing_source",
    "inv.account_tax_treatment_matches_producing_source",
    "inv.account_owner_matches_producing_source"
  ),
  depends_on (governed.customer)
);

-- logical.account: one dated statement per account, versioned, rebuilt FULL from the
-- complete change feed: raw.customer_mgmt_action (received records; only NEW, ADDACCT,
-- UPDACCT, CLOSEACCT carry an account subject) and ce.account_changes (labeled constructed
-- scenarios; provenance is never null here, and never populated for received records).
WITH from_actions AS (
  SELECT
    ca_id AS account_number,
    action_ts AS effective_from,
    -- handoff.raw.customer_mgmt_action.c_id->logical.account.owning_customer_number
    -- supplied directly by every account action row.
    c_id AS owning_customer_number_as_reported,
    -- handoff.raw.customer_mgmt_action.action_type->logical.account.status
    -- status_from_action_meaning (sources-v1.json action_type_meanings: NEW, ADDACCT,
    -- UPDACCT -> open; CLOSEACCT -> closed), using the anchored status_codes (ACTV/INAC).
    CASE action_type
      WHEN 'NEW' THEN 'ACTV'
      WHEN 'ADDACCT' THEN 'ACTV'
      WHEN 'UPDACCT' THEN 'ACTV'
      WHEN 'CLOSEACCT' THEN 'INAC'
    END AS status,
    -- handoff.raw.customer_mgmt_action.ca_tax_st->logical.account.tax_treatment
    -- CLOSEACCT omits ca_tax_st (sources-v1.json action_type_meanings.fields_present); the
    -- omission is resolved below via carried_forward_from_previous_statement.
    CASE WHEN action_type IN ('NEW', 'ADDACCT', 'UPDACCT') THEN ca_tax_st ELSE NULL END AS tax_treatment_as_reported,
    CAST(NULL AS VARCHAR) AS provenance
  FROM raw.customer_mgmt_action
  WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
),
from_constructed AS (
  SELECT
    -- handoff.ce.account_changes.account_id->logical.account.account_number
    account_id AS account_number,
    -- handoff.ce.account_changes.action_at->logical.account.effective_from
    action_at AS effective_from,
    -- ce.account_changes carries no owner of its own; resolved below via
    -- carried_forward_from_previous_statement (L1.omitted-facts-stand).
    CAST(NULL AS BIGINT) AS owning_customer_number_as_reported,
    -- handoff.ce.account_changes.status_id->logical.account.status, already coded with the
    -- anchored status_codes (ACTV/INAC).
    CASE status_id
      WHEN 'ACTV' THEN 'ACTV'
      WHEN 'INAC' THEN 'INAC'
    END AS status,
    -- handoff.ce.account_changes.tax_status_id->logical.account.tax_treatment
    tax_status_id AS tax_treatment_as_reported,
    -- handoff.ce.account_changes.provenance->logical.account.provenance
    provenance
  FROM ce.account_changes
),
unioned AS (
  SELECT * FROM from_actions
  UNION ALL
  SELECT * FROM from_constructed
),
filled AS (
  SELECT
    account_number,
    effective_from,
    status,
    provenance,
    -- logical.account.owning_customer_number: carried_forward_from_previous_statement
    -- (L1.omitted-facts-stand) when the producing row (ce.account_changes) supplies no owner.
    LAST_VALUE(owning_customer_number_as_reported IGNORE NULLS) OVER (
      PARTITION BY account_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS owning_customer_number,
    -- logical.account.tax_treatment: carried_forward_from_previous_statement when the
    -- producing action (CLOSEACCT) omits ca_tax_st.
    LAST_VALUE(tax_treatment_as_reported IGNORE NULLS) OVER (
      PARTITION BY account_number
      ORDER BY effective_from
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS tax_treatment
  FROM unioned
)
SELECT
  account_number,
  effective_from,
  -- logical.account.is_current: computed_within_entity, true when no statement of the same
  -- account_number has a later effective_from than this one.
  effective_from = MAX(effective_from) OVER (PARTITION BY account_number) AS is_current,
  owning_customer_number,
  status,
  tax_treatment,
  provenance
FROM filled;
