-- inv.account_single_current: for any account_number, at most one statement
-- has is_current = true, always. If any statement of that account exists, the
-- record still stands under its own history (no statement of that account is
-- a withdrawal) and its owning customer still stands (no withdrawal statement
-- of that customer at all, per L1.owner-standing's extended second sentence),
-- exactly one is current; if either condition fails, none is current. Zero
-- rows means the invariant holds.
--
-- owning_customer_number is read from governed.account itself, which is this
-- entity's own written table, not an out-of-containment read; the owner's
-- withdrawal history is governed.customer, this entity's sibling within the
-- same job, which an audit may read freely (unlike an artifact's projection
-- SQL, an audit checks compiled behavior against every entity this job
-- writes).

WITH acct AS (
    SELECT
        account_number,
        SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_count,
        SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) AS own_withdrawal_count,
        MAX(owning_customer_number) AS owning_customer_number
    FROM governed.account
    GROUP BY account_number
),
owner_withdrawn AS (
    SELECT DISTINCT customer_number
    FROM governed.customer
    WHERE is_withdrawal
)
SELECT acct.account_number
FROM acct
LEFT JOIN owner_withdrawn ow ON ow.customer_number = acct.owning_customer_number
WHERE acct.current_count > 1
   OR (
        acct.current_count = 0
        AND acct.own_withdrawal_count = 0
        AND ow.customer_number IS NULL
      );
