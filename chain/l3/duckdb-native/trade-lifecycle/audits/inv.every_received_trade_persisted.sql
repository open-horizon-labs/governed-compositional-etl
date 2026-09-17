-- inv.every_received_trade_persisted (L2 cycle 4, new): for any trade_number
-- none of whose received reports carries cdc_flag D, exactly one
-- governed.trade row exists for that trade_number. A trade_number is
-- reported by raw.trade_cdc (any batch) or raw.trade_history; raw.trade_cdc
-- rows carry cdc_flag, tested here as cdc_flag IS DISTINCT FROM 'D' so a
-- report whose cdc_flag happens to be null still counts as not-D and stays
-- in scope; raw.trade_history carries no cdc_flag column at all, so its
-- reports can never disqualify a trade_number. A trade_number with any
-- cdc_flag D report anywhere in raw.trade_cdc is L1.hole.deletions' case and
-- is excluded from this invariant's claim entirely, per the model's own
-- review_trigger, whether or not it also has a duplicate or missing
-- governed.trade row. Among qualifying (non-deleted) trade_numbers, both a
-- missing governed.trade row and more than one governed.trade row are
-- violations; zero rows means the invariant holds.

WITH reported_trade_numbers AS (
    SELECT DISTINCT t_id AS trade_number FROM raw.trade_cdc
    UNION
    SELECT DISTINCT th_t_id AS trade_number FROM raw.trade_history
),
trade_cdc_never_deleted AS (
    SELECT
        t_id AS trade_number,
        BOOL_AND(cdc_flag IS DISTINCT FROM 'D') AS none_carry_delete
    FROM raw.trade_cdc
    GROUP BY t_id
),
qualifying_trade_numbers AS (
    SELECT r.trade_number
    FROM reported_trade_numbers AS r
    LEFT JOIN trade_cdc_never_deleted AS d ON d.trade_number = r.trade_number
    -- No raw.trade_cdc row at all (history-only identity, unexpected but not
    -- this invariant's concern) counts as no D report either: COALESCE to
    -- true keeps such a trade_number qualifying.
    WHERE COALESCE(d.none_carry_delete, TRUE)
)
SELECT
    q.trade_number,
    COUNT(t.trade_number) AS governed_row_count
FROM qualifying_trade_numbers AS q
LEFT JOIN governed.trade AS t ON t.trade_number = q.trade_number
GROUP BY q.trade_number
HAVING COUNT(t.trade_number) <> 1;
