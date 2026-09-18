AUDIT (name "inv.account_asof_carries_customer_asof");

-- For any account_number and moment T, if the account has an as-of answer at T, the
-- customer named by that answer's owning_customer_number must also have an as-of answer at
-- the same T; a withdrawal of the customer at or before T (reversal-foreclosure, per
-- L1.hole.deletion-reversal) means it does not. The account's as-of answer is never half an
-- answer with the owner's part missing, per L1.owner-standing.
--
-- T is not instantiated only at the account's own effective_from values: for an
-- owner-withdrawn account, every one of the account's own statements predates the owner's
-- withdrawal, so testing only at those moments checks the owner branch exactly where it
-- cannot fire, making the audit vacuous for the one case it exists to catch. T also ranges
-- over every withdrawal moment of every customer the account has ever been owned by, so the
-- audit tests the moment the owner's answer actually disappears, not only moments before it.
WITH customer_withdrawal_bound AS (
  SELECT
    customer_number,
    MIN(effective_from) AS first_withdrawal_from
  FROM governed.customer
  WHERE is_withdrawal
  GROUP BY customer_number
),
account_owners AS (
  SELECT DISTINCT account_number, owning_customer_number
  FROM @this_model
  WHERE owning_customer_number IS NOT NULL
),
t_values AS (
  SELECT account_number, effective_from AS t
  FROM @this_model
  UNION
  SELECT ao.account_number, cw.first_withdrawal_from AS t
  FROM account_owners AS ao
  JOIN customer_withdrawal_bound AS cw
    ON cw.customer_number = ao.owning_customer_number
),
account_asof AS (
  SELECT
    tv.account_number,
    tv.t,
    -- the owning_customer_number named by the account's as-of answer at T, if any
    (
      SELECT a2.owning_customer_number
      FROM @this_model AS a2
      WHERE a2.account_number = tv.account_number
        AND a2.effective_from <= tv.t
      ORDER BY a2.effective_from DESC
      LIMIT 1
    ) AS owner_at_t,
    EXISTS (
      SELECT 1
      FROM @this_model AS aw
      WHERE aw.account_number = tv.account_number
        AND aw.is_withdrawal
        AND aw.effective_from <= tv.t
    ) AS account_withdrawn_by_t,
    EXISTS (
      SELECT 1
      FROM @this_model AS a3
      WHERE a3.account_number = tv.account_number
        AND a3.effective_from <= tv.t
    ) AS account_has_statement_by_t
  FROM t_values AS tv
)
SELECT
  aa.account_number,
  aa.t
FROM account_asof AS aa
WHERE aa.account_has_statement_by_t
  AND NOT aa.account_withdrawn_by_t
  AND (
    aa.owner_at_t IS NULL
    OR EXISTS (
      SELECT 1
      FROM customer_withdrawal_bound AS cw
      WHERE cw.customer_number = aa.owner_at_t
        AND cw.first_withdrawal_from <= aa.t
    )
    OR NOT EXISTS (
      SELECT 1
      FROM governed.customer AS c
      WHERE c.customer_number = aa.owner_at_t
        AND c.effective_from <= aa.t
    )
  );
