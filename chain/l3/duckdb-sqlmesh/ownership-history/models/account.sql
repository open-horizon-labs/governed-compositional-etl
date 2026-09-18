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
    "inv.account_owner_matches_producing_source",
    "inv.unknown_codes_held",
    "inv.account_statement_never_created_by_activity",
    "inv.withdrawal_never_reaches_account_status",
    "inv.customer_withdrawal_with_standing_accounts_reported"
  ),
  depends_on (governed.customer)
);

-- logical.account: one dated statement per account, versioned, rebuilt FULL from the
-- complete change feed: raw.customer_mgmt_action (received records; only NEW, ADDACCT,
-- UPDACCT, CLOSEACCT carry an account subject) and ce.account_changes (labeled constructed
-- scenarios; provenance is never null here, and never populated for received records).
--
-- logical.account.is_withdrawal: computed_within_entity. Neither candidate source can
-- express a withdrawal -- raw.customer_mgmt_action's action_type vocabulary names no
-- withdrawal action, and ce.account_changes carries no field that could signal one -- so
-- every statement this job currently produces has is_withdrawal = false. The only handoff
-- that could ever set it true is raw.account_cdc.cdc_flag = 'D', which remains deferred
-- under L1.hole.change-effective-time and is not selected for this cycle; no handoff is
-- invented from it here.
WITH from_actions AS (
  SELECT
    ca_id AS account_number,
    action_ts AS effective_from,
    FALSE AS is_withdrawal,
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
    -- ce.account_changes carries no field that could signal a withdrawal.
    FALSE AS is_withdrawal,
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
    is_withdrawal,
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
),
-- logical.account.is_current's own-withdrawal, reversal-foreclosure branch: once an
-- account's own record carries a withdrawal, no statement of that account_number at or
-- after that withdrawal's own moment is ever current again (L1.hole.deletion-reversal).
account_withdrawal_bound AS (
  SELECT
    account_number,
    MIN(effective_from) AS first_withdrawal_from
  FROM filled
  WHERE is_withdrawal
  GROUP BY account_number
),
-- logical.account.is_current's owner-cascade branch: an account has no standing when its
-- owning customer has been withdrawn at all, at any moment, regardless of how long ago the
-- account's own last statement was dated (L1.owner-standing's extended second sentence).
-- This is the cross-entity read: it consults the SIBLING logical.customer entity's own
-- is_withdrawal fact via governed.customer, not anything derivable from logical.account's
-- own rows. The check is existence-only -- whether the owning customer has ANY withdrawal
-- at all -- not a date comparison against this statement's own effective_from, because
-- "current" asks about standing at an unbounded, ever-advancing present, not at the moment
-- this statement was dated.
customer_withdrawn AS (
  SELECT DISTINCT customer_number
  FROM governed.customer
  WHERE is_withdrawal
)
SELECT
  f.account_number,
  f.effective_from,
  -- logical.account.is_current: computed_within_entity, per its full rule text (the label
  -- undersells this -- one branch below reads the sibling logical.customer entity):
  -- false when this statement's own is_withdrawal is true;
  -- false when a withdrawal statement of the same account_number has an effective_from at
  --   or before this statement's effective_from (own-withdrawal, reversal-foreclosure);
  -- false when this statement's owning_customer_number's customer entity has ANY
  --   withdrawal statement at all, at any effective_from, existence-only, no date
  --   comparison against this statement's own effective_from (owner-cascade,
  --   L1.owner-standing's extended second sentence via the sibling logical.customer entity);
  -- otherwise true when no statement of the same account_number has a later effective_from
  --   than this one, false when one does.
  CASE
    WHEN f.is_withdrawal THEN FALSE
    WHEN aw.first_withdrawal_from IS NOT NULL AND aw.first_withdrawal_from <= f.effective_from THEN FALSE
    WHEN cw.customer_number IS NOT NULL THEN FALSE
    ELSE f.effective_from = MAX(f.effective_from) OVER (PARTITION BY f.account_number)
  END AS is_current,
  f.is_withdrawal,
  f.owning_customer_number,
  f.status,
  f.tax_treatment,
  f.provenance
FROM filled AS f
LEFT JOIN account_withdrawal_bound AS aw
  ON aw.account_number = f.account_number
LEFT JOIN customer_withdrawn AS cw
  ON cw.customer_number = f.owning_customer_number;
