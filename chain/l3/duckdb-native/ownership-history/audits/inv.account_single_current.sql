-- inv.account_single_current: for any account_number, at most one statement
-- has is_current = true, always. If any statement of that account exists, the
-- record still stands under its own history (no statement of that account is
-- a withdrawal) and its owning customer still stands (no withdrawal statement
-- of that customer at all, per L1.owner-standing's extended second sentence),
-- exactly one is current; if either condition fails, none is current. Zero
-- rows means the invariant holds.
--
-- The owner condition is evaluated per statement, against that statement's
-- OWN owning_customer_number -- specifically the account's own latest
-- statement's owning_customer_number, since is_current can only ever be true
-- for the latest statement, and logical.account.is_current's own cascade
-- checks that statement's own owner, not some aggregate across the account's
-- history. An account whose owner changed across its own statements (e.g.
-- owned by customer 9 in 2010, then by withdrawn customer 5 in 2015) must be
-- checked against customer 5, the latest statement's owner, not against
-- whichever owning_customer_number a MAX() or MIN() happens to pick.
--
-- governed.customer is this entity's sibling within the same job, which an
-- audit may read freely (unlike an artifact's projection SQL, an audit
-- checks compiled behavior against every entity this job writes).

WITH latest_statement AS (
    SELECT a.account_number, a.owning_customer_number
    FROM governed.account a
    WHERE a.effective_from = (
        SELECT MAX(a2.effective_from)
        FROM governed.account a2
        WHERE a2.account_number = a.account_number
    )
),
acct AS (
    SELECT
        account_number,
        SUM(CASE WHEN is_current THEN 1 ELSE 0 END) AS current_count,
        SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) AS own_withdrawal_count
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
JOIN latest_statement ls ON ls.account_number = acct.account_number
LEFT JOIN owner_withdrawn ow ON ow.customer_number = ls.owning_customer_number
WHERE acct.current_count > 1
   OR (
        acct.current_count = 0
        AND acct.own_withdrawal_count = 0
        AND ow.customer_number IS NULL
      );
