-- inv.trade_placement_reference_frozen (L2 cycle 2): for any trade_number,
-- placed_at, owning_account_effective_from, owning_customer_number, and
-- owning_customer_effective_from are each set once -- from the trade's
-- first-encountered report (across both anchored sources, raw.trade_history
-- preferred where it exists) and the account and customer statements resolved
-- as of that report's own time -- and are never replaced by a later report of
-- the same trade. Checked two ways: (1) recomputing the frozen quadruple
-- independently from raw.trade_cdc, raw.trade_history, governed.account, and
-- governed.customer, and diffing against what governed.trade actually
-- persisted; (2) the review_trigger's own literal form -- no report of a
-- trade, from either anchored source, carries an event time earlier than its
-- recorded placed_at. Zero rows means the invariant holds.

WITH first_cdc_report AS (
    SELECT t_id, t_dts, t_ca_id
    FROM raw.trade_cdc
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts
    FROM raw.trade_history
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
first_report AS (
    SELECT
        fc.t_id AS trade_number,
        COALESCE(fh.th_dts, fc.t_dts) AS placed_at,
        fc.t_ca_id AS owning_account_number
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
),
recomputed_account_pin AS (
    SELECT
        fr.trade_number,
        fr.placed_at,
        acct.effective_from AS owning_account_effective_from,
        acct.owning_customer_number AS owning_customer_number
    FROM first_report fr
    LEFT JOIN governed.account acct
      ON acct.account_number = fr.owning_account_number
     AND acct.effective_from <= fr.placed_at
    QUALIFY ROW_NUMBER() OVER (PARTITION BY fr.trade_number ORDER BY acct.effective_from DESC NULLS LAST) = 1
),
recomputed_pin AS (
    SELECT
        ap.trade_number,
        ap.placed_at,
        ap.owning_account_effective_from,
        ap.owning_customer_number,
        cust.effective_from AS owning_customer_effective_from
    FROM recomputed_account_pin ap
    LEFT JOIN governed.customer cust
      ON cust.customer_number = ap.owning_customer_number
     AND cust.effective_from <= ap.placed_at
    QUALIFY ROW_NUMBER() OVER (PARTITION BY ap.trade_number ORDER BY cust.effective_from DESC NULLS LAST) = 1
)
SELECT t.trade_number, 'frozen_reference_mismatch' AS problem
FROM governed.trade t
JOIN recomputed_pin rp ON rp.trade_number = t.trade_number
WHERE rp.placed_at IS DISTINCT FROM t.placed_at
   OR rp.owning_account_effective_from IS DISTINCT FROM t.owning_account_effective_from
   OR rp.owning_customer_number IS DISTINCT FROM t.owning_customer_number
   OR rp.owning_customer_effective_from IS DISTINCT FROM t.owning_customer_effective_from

UNION ALL

SELECT tc.t_id AS trade_number, 'later_cdc_report_earlier_event_time' AS problem
FROM raw.trade_cdc tc
JOIN governed.trade t ON t.trade_number = tc.t_id
WHERE t.placed_at IS NULL OR tc.t_dts < t.placed_at

UNION ALL

SELECT th.th_t_id AS trade_number, 'later_history_report_earlier_event_time' AS problem
FROM raw.trade_history th
JOIN governed.trade t ON t.trade_number = th.th_t_id
WHERE t.placed_at IS NULL OR th.th_dts < t.placed_at;
