-- inv.account_asof_carries_customer_asof: for any account_number and moment
-- T, if the account has an as-of answer at T the customer entity must have
-- an as-of answer for that account's owning_customer_number at the same
-- moment T; the account's as-of answer is never half an answer with the
-- owner's part missing, per L1.owner-standing's "an account has no standing
-- at a moment when its owner has none."
--
-- Using each account statement's own effective_from as a representative
-- moment T: the account "has an answer" at T when this statement is not
-- itself a withdrawal and no earlier-or-equal withdrawal of the same account
-- exists. The customer "has an answer" at T when a customer statement of the
-- owning_customer_number is effective at or before T and no withdrawal of
-- that customer has an effective_from at or before T (reversal-foreclosure).
-- Zero rows means the invariant holds.

WITH customer_withdrawals AS (
    SELECT customer_number, MIN(effective_from) AS first_withdrawal_from
    FROM governed.customer
    WHERE is_withdrawal
    GROUP BY customer_number
)
SELECT a.account_number, a.effective_from
FROM governed.account a
LEFT JOIN customer_withdrawals cw ON cw.customer_number = a.owning_customer_number
WHERE
    -- the account itself has an as-of answer at T = its own effective_from
    NOT a.is_withdrawal
    AND NOT EXISTS (
        SELECT 1 FROM governed.account a2
        WHERE a2.account_number = a.account_number
          AND a2.is_withdrawal
          AND a2.effective_from <= a.effective_from
    )
    -- but the customer does not
    AND (
        a.owning_customer_number IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM governed.customer c
            WHERE c.customer_number = a.owning_customer_number
              AND c.effective_from <= a.effective_from
        )
        OR (cw.customer_number IS NOT NULL AND cw.first_withdrawal_from <= a.effective_from)
    );
