-- inv.account_position_key_matches_holding_change: account_number and
-- account_effective_from equal the owning_account_number and
-- owning_account_effective_from shared by every logical.holding_change row
-- grouped into this row. Checked by recomputing the distinct group keys
-- directly from governed.holding_change and comparing them, null-safely, to
-- governed.account_position's own persisted keys via a full outer join; any
-- key present on only one side (including a side made unmatched by a null
-- key value) surfaces as a violation. Zero rows means the invariant holds.

WITH recomputed_keys AS (
    SELECT DISTINCT
        owning_account_number AS account_number,
        owning_account_effective_from AS account_effective_from
    FROM governed.holding_change
)
SELECT
    COALESCE(r.account_number, ap.account_number) AS account_number,
    COALESCE(r.account_effective_from, ap.account_effective_from) AS account_effective_from
FROM recomputed_keys AS r
FULL OUTER JOIN governed.account_position AS ap
  ON ap.account_number IS NOT DISTINCT FROM r.account_number
 AND ap.account_effective_from IS NOT DISTINCT FROM r.account_effective_from
WHERE r.account_number IS NULL
   OR ap.account_number IS NULL;
