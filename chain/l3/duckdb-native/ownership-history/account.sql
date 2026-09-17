-- logical.account: versioned entity, one dated statement per account.
-- Two selected sources feed it:
--   raw.customer_mgmt_action (received records: NEW/ADDACCT/UPDACCT/CLOSEACCT
--     rows have an account subject per action_type_meanings.subjects) supplies
--     account_number, effective_from, owning_customer_number, status, and
--     tax_treatment directly; provenance is NULL (not a constructed scenario).
--   ce.account_changes (labeled constructed scenarios) supplies account_number,
--     effective_from, status, tax_treatment, and provenance directly, but no
--     owning_customer_number of its own.
--
-- derived_from:
--   logical.account, logical.account.account_number, logical.account.effective_from,
--   logical.account.is_current, logical.account.owning_customer_number,
--   logical.account.status, logical.account.tax_treatment, logical.account.provenance,
--   type.account_number, type.statement_effective_from, type.statement_is_current,
--   type.account_owner_reference, type.account_standing_status,
--   type.account_tax_treatment, type.constructed_scenario_label,
--   handoff.raw.customer_mgmt_action.ca_id->logical.account.account_number,
--   handoff.raw.customer_mgmt_action.action_ts->logical.account.effective_from,
--   handoff.raw.customer_mgmt_action.c_id->logical.account.owning_customer_number,
--   handoff.raw.customer_mgmt_action.action_type->logical.account.status,
--   handoff.raw.customer_mgmt_action.ca_tax_st->logical.account.tax_treatment,
--   handoff.ce.account_changes.account_id->logical.account.account_number,
--   handoff.ce.account_changes.action_at->logical.account.effective_from,
--   handoff.ce.account_changes.status_id->logical.account.status,
--   handoff.ce.account_changes.tax_status_id->logical.account.tax_treatment,
--   handoff.ce.account_changes.provenance->logical.account.provenance
--
-- reads: raw.customer_mgmt_action, ce.account_changes
--
-- Strategy: strategy_for_versioned (CREATE OR REPLACE TABLE AS from the complete
-- change feed). No updates in place; per_statement values are never updated.
--
-- status selector "status_from_action_meaning" (historical rows): NEW, ADDACCT,
-- UPDACCT -> ACTV; CLOSEACCT -> INAC. ce.account_changes.status_id already uses
-- the anchored status_codes vocabulary (ACTV/INAC) directly, so it passes through
-- unchanged.
--
-- owning_customer_number selector "carried_forward_from_previous_statement": a
-- constructed change (ce.account_changes supplies no owner of its own) takes the
-- value carried by this account's immediately preceding statement, ordered by
-- effective_from across both sources combined. inv.constructed_account_change_
-- refers_to_known_account guarantees a constructed change always has an earlier,
-- owner-bearing statement to carry forward from.
--
-- is_current selector "computed_within_entity": true when no statement of the
-- same account_number has a later effective_from than this one.

CREATE OR REPLACE TABLE governed.account AS
WITH historical AS (
    SELECT
        ca_id AS account_number,
        action_ts AS effective_from,
        c_id AS owning_customer_number,
        CASE action_type
            WHEN 'NEW'      THEN 'ACTV'
            WHEN 'ADDACCT'  THEN 'ACTV'
            WHEN 'UPDACCT'  THEN 'ACTV'
            WHEN 'CLOSEACCT' THEN 'INAC'
        END AS status,
        ca_tax_st AS tax_treatment,
        CAST(NULL AS VARCHAR) AS provenance
    FROM raw.customer_mgmt_action
    WHERE action_type IN ('NEW', 'ADDACCT', 'UPDACCT', 'CLOSEACCT')
),
constructed AS (
    SELECT
        account_id AS account_number,
        action_at AS effective_from,
        CAST(NULL AS BIGINT) AS owning_customer_number,
        status_id AS status,
        tax_status_id AS tax_treatment,
        provenance
    FROM ce.account_changes
),
combined AS (
    SELECT * FROM historical
    UNION ALL
    SELECT * FROM constructed
),
carried AS (
    SELECT
        account_number,
        effective_from,
        COALESCE(
            owning_customer_number,
            LAST_VALUE(owning_customer_number IGNORE NULLS) OVER (
                PARTITION BY account_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS owning_customer_number,
        status,
        tax_treatment,
        provenance
    FROM combined
)
SELECT
    account_number,
    effective_from,
    (effective_from = MAX(effective_from) OVER (PARTITION BY account_number)) AS is_current,
    owning_customer_number,
    status,
    tax_treatment,
    provenance
FROM carried;
