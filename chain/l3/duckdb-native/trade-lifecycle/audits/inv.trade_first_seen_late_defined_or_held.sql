-- inv.trade_first_seen_late_defined_or_held: for any trade_number,
-- first_seen_late is null if and only if the trade is held: either
-- inv.unknown_codes_held reports its first-encountered report's status or
-- order type as outside the anchored vocabularies, or
-- inv.trade_market_order_seen_pending_held reports it as a market order
-- first reported PNDG. first_seen_late is non-null (true or false) for
-- every other trade. Zero rows means the invariant holds.

WITH valid_cdc_rows AS (
    -- A row carrying any code outside its anchored vocabulary in any of
    -- cdc_flag, t_st_id, t_tt_id is held in its entirety; a trade whose
    -- only raw.trade_cdc report is held never reaches first_cdc_report and
    -- therefore never reaches governed.trade at all (see
    -- inv.every_received_trade_persisted), so this invariant's join below
    -- naturally excludes it too.
    SELECT *
    FROM raw.trade_cdc
    WHERE cdc_flag IN ('I', 'U', 'D')
      AND t_st_id IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
      AND t_tt_id IN ('TLB', 'TLS', 'TMB', 'TMS')
),
first_cdc_report AS (
    SELECT t_id, t_st_id, t_tt_id
    FROM valid_cdc_rows
    QUALIFY ROW_NUMBER() OVER (PARTITION BY t_id ORDER BY batch_date, cdc_dsn) = 1
),
first_history_report AS (
    SELECT th_t_id, th_dts, th_st_id
    FROM raw.trade_history
    QUALIFY ROW_NUMBER() OVER (PARTITION BY th_t_id ORDER BY th_dts) = 1
),
first_report AS (
    SELECT
        fc.t_id AS trade_number,
        fc.t_tt_id AS raw_order_type,
        COALESCE(fh.th_st_id, fc.t_st_id) AS first_status
    FROM first_cdc_report fc
    LEFT JOIN first_history_report fh ON fh.th_t_id = fc.t_id
),
expected AS (
    SELECT
        trade_number,
        (
            first_status NOT IN ('PNDG', 'SBMT', 'CMPT', 'CNCL')
            OR (raw_order_type IN ('TMB', 'TMS') AND first_status = 'PNDG')
        ) AS expected_held
    FROM first_report
)
SELECT t.trade_number, t.first_seen_late, e.expected_held
FROM governed.trade AS t
JOIN expected AS e ON e.trade_number = t.trade_number
WHERE (t.first_seen_late IS NULL) IS DISTINCT FROM e.expected_held;
