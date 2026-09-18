AUDIT (name "inv.account_asof_carries_customer_asof");

-- For any account statement that itself has an as-of answer (is_withdrawal = false), the
-- customer named by owning_customer_number must also have an as-of answer at the same
-- moment T = this statement's own effective_from: a customer statement effective at or
-- before T must exist, and no withdrawal statement of that customer may have an
-- effective_from at or before T (reversal-foreclosure, per L1.hole.deletion-reversal). The
-- account's as-of answer is never half an answer with the owner's part missing, per
-- L1.owner-standing.
WITH customer_withdrawal_bound AS (
  SELECT
    customer_number,
    MIN(effective_from) AS first_withdrawal_from
  FROM governed.customer
  WHERE is_withdrawal
  GROUP BY customer_number
)
SELECT
  a.account_number,
  a.effective_from
FROM @this_model AS a
LEFT JOIN customer_withdrawal_bound AS w
  ON w.customer_number = a.owning_customer_number
WHERE a.is_withdrawal = FALSE
  AND (
    a.owning_customer_number IS NULL
    OR (w.first_withdrawal_from IS NOT NULL AND w.first_withdrawal_from <= a.effective_from)
    OR NOT EXISTS (
      SELECT 1
      FROM governed.customer AS c
      WHERE c.customer_number = a.owning_customer_number
        AND c.effective_from <= a.effective_from
    )
  );
