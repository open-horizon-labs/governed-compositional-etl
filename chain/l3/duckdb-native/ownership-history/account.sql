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
--   logical.account.is_current, logical.account.is_withdrawal,
--   logical.account.owning_customer_number, logical.account.status,
--   logical.account.tax_treatment, logical.account.provenance,
--   type.account_number, type.statement_effective_from, type.statement_is_current,
--   type.statement_is_withdrawal, type.account_owner_reference,
--   type.account_standing_status, type.account_tax_treatment,
--   type.constructed_scenario_label,
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
-- reads: raw.customer_mgmt_action, ce.account_changes, governed.customer
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
-- tax_treatment selector "carried_forward_from_previous_statement" (L2 cycle 2):
-- CLOSEACCT omits ca_tax_st (L1.omitted-facts-stand: the omitted fact stands as
-- it last stood), so tax_treatment equals the value carried by this account's
-- immediately preceding statement, ordered by effective_from across both
-- sources combined. CLOSEACCT's anchored meaning presupposes an existing
-- account (only NEW or ADDACCT first records one), so a preceding statement is
-- guaranteed to exist. ce.account_changes always supplies tax_status_id
-- directly, so this carry-forward only ever fills a gap left by CLOSEACCT.
--
-- is_withdrawal "computed_within_entity" (L2 cycle 3): false for every
-- statement produced by raw.customer_mgmt_action (its action_type vocabulary
-- names no withdrawal action) and false for every statement produced by
-- ce.account_changes (its anchored fields carry no withdrawal signal). The
-- account CDC handoff that could set this true (raw.account_cdc.cdc_flag = 'D')
-- is deferred under L1.hole.change-effective-time and is not read here; this
-- attribute is therefore always false for every statement this job currently
-- produces.
--
-- is_current "computed_within_entity" (L2 cycle 3, amended), with the
-- L1.owner-standing cascade -- THE CROSS-ENTITY BRANCH: false when this
-- statement's own is_withdrawal is true; false when a withdrawal statement of
-- the same account_number has an effective_from at or before this statement's
-- own effective_from (reversal-foreclosure); false when the customer named by
-- this account's owning_customer_number carries ANY withdrawal statement at
-- all, at any effective_from (the owner-standing cascade -- an account has no
-- standing when its owner has none, checked against existence, not against
-- this statement's own effective_from, since "current" asks about an unbounded
-- present); otherwise true when no statement of the same account_number has a
-- later effective_from than this one, false when one does.
--
-- The owner-standing branch is a computation over the SIBLING logical.customer
-- entity, which logical.account.is_current's derivation rule states in full
-- even though its own kind label (computed_within_entity) has no vocabulary
-- for a two-entity computation -- the rule governs, not the label (see
-- DEVELOPER-CONTRACT-L2-L3.md, "The rule text governs, not the derivation's
-- label"). This file reads governed.customer directly, filtered to
-- is_withdrawal, and checks EXISTENCE of any withdrawal for the owning
-- customer_number -- never a date comparison against this account
-- statement's own effective_from. A withdrawal creates no account statement,
-- so an owner-withdrawn account's own statements are all necessarily dated
-- before the withdrawal; comparing dates would mean this branch could never
-- fire, which is exactly the form two L2 review rounds rejected. "Current"
-- asks about standing at an unbounded present, not at this statement's own
-- moment, so the mere existence of an owner withdrawal (however dated)
-- forecloses currency (see logical.account.is_current's parallel_assumption
-- and rule text). No selected handoff names this cross-entity read (the
-- schema has no label for a computation spanning two entities of one job),
-- so it is an undeclared dependency the gate now surfaces to the reviewer as
-- a question rather than passing silently -- see chain_l3.py's updated
-- containment(), which now permits a job's own sibling entities as reads
-- alongside handoff sources and upstream jobs.
--
-- This job currently produces no customer statement with is_withdrawal =
-- true (raw.customer_cdc.cdc_flag is deferred), so this branch is
-- unexercised by today's fixture, but it is wired to the actual compiled
-- customer entity rather than re-derived from a source that can never
-- express a withdrawal -- it will fire the moment governed.customer ever
-- carries one, with no further change to this file required.
--
-- owning_customer_number/status/tax_treatment: null exactly when is_withdrawal
-- is true (never today), since a withdrawal asserts no standing at all.

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
        CAST(NULL AS VARCHAR) AS provenance,
        -- raw.customer_mgmt_action's action_type vocabulary names no account
        -- withdrawal action; the CDC source that could set this true is
        -- deferred.
        FALSE AS is_withdrawal
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
        provenance,
        -- ce.account_changes as anchored carries no field that could signal a
        -- withdrawal (see logical.account.is_withdrawal's note).
        FALSE AS is_withdrawal
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
        is_withdrawal,
        COALESCE(
            owning_customer_number,
            LAST_VALUE(owning_customer_number IGNORE NULLS) OVER (
                PARTITION BY account_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS owning_customer_number_carried,
        status AS status_raw,
        COALESCE(
            tax_treatment,
            LAST_VALUE(tax_treatment IGNORE NULLS) OVER (
                PARTITION BY account_number ORDER BY effective_from
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            )
        ) AS tax_treatment_carried,
        provenance
    FROM combined
),
account_withdrawals AS (
    SELECT account_number, MIN(effective_from) AS first_withdrawal_from
    FROM carried
    WHERE is_withdrawal
    GROUP BY account_number
),
-- The cross-entity branch: every customer_number the sibling logical.customer
-- entity has ever withdrawn, read directly from governed.customer (this
-- job's own compiled entity, not re-derived from a source that can never
-- express a withdrawal). Keyed on existence only -- no date comparison.
customer_owner_withdrawals AS (
    SELECT DISTINCT customer_number
    FROM governed.customer
    WHERE is_withdrawal
)
SELECT
    a.account_number,
    a.effective_from,
    CASE
        WHEN a.is_withdrawal THEN FALSE
        WHEN aw.first_withdrawal_from IS NOT NULL AND aw.first_withdrawal_from <= a.effective_from THEN FALSE
        WHEN EXISTS (
            SELECT 1 FROM customer_owner_withdrawals cow
            WHERE cow.customer_number = a.owning_customer_number_carried
        ) THEN FALSE
        WHEN a.effective_from = MAX(a.effective_from) OVER (PARTITION BY a.account_number) THEN TRUE
        ELSE FALSE
    END AS is_current,
    a.is_withdrawal,
    CASE WHEN a.is_withdrawal THEN NULL ELSE a.owning_customer_number_carried END AS owning_customer_number,
    CASE WHEN a.is_withdrawal THEN NULL ELSE a.status_raw END AS status,
    CASE WHEN a.is_withdrawal THEN NULL ELSE a.tax_treatment_carried END AS tax_treatment,
    a.provenance
FROM carried a
LEFT JOIN account_withdrawals aw ON aw.account_number = a.account_number;
