-- inv.trade_placement_reference_frozen: for any trade_number, placed_at,
-- owning_account_effective_from, and owning_customer_number are each set once
-- -- from the trade's first-encountered report and the account statement
-- resolved as of that report's own time -- and are never replaced by a later
-- report of the same trade. Checked two ways: (1) recomputing the frozen
-- triple independently from raw.trade_cdc and governed.account and diffing
-- against what governed.trade actually persisted; (2) the review_trigger's
-- own literal form -- no report of a trade carries an event time earlier than
-- its recorded placed_at. Zero rows means the invariant holds.

WITH first_report AS (
    SELECT t_id, t_dts, t_ca_id
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
recomputed_pin AS (
    SELECT
        fr.t_id AS trade_number,
        fr.t_dts AS placed_at,
        acct.effective_from AS owning_account_effective_from,
        acct.owning_customer_number AS owning_customer_number
    FROM first_report fr
    LEFT JOIN governed.account acct
      ON acct.account_number = fr.t_ca_id
     AND acct.effective_from <= fr.t_dts
    QUALIFY ROW_NUMBER() OVER (PARTITION BY fr.t_id ORDER BY acct.effective_from DESC NULLS LAST) = 1
)
SELECT t.trade_number, 'frozen_reference_mismatch' AS problem
FROM governed.trade t
JOIN recomputed_pin rp ON rp.trade_number = t.trade_number
WHERE rp.placed_at <> t.placed_at
   OR rp.owning_account_effective_from IS DISTINCT FROM t.owning_account_effective_from
   OR rp.owning_customer_number IS DISTINCT FROM t.owning_customer_number

UNION ALL

SELECT tc.t_id AS trade_number, 'later_report_earlier_event_time' AS problem
FROM raw.trade_cdc tc
JOIN governed.trade t ON t.trade_number = tc.t_id
WHERE tc.t_dts < t.placed_at;
