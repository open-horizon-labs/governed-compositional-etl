AUDIT (name "inv.account_asof_carries_customer_asof");

-- For any account_number and moment T, if the account has an as-of answer at T, the
-- customer named by that answer's owning_customer_number must also have an as-of answer at
-- the same T. The account's as-of answer is never half an answer with the owner's part
-- missing, per L1.owner-standing.
--
-- T is not instantiated only at the account's own effective_from values: for an
-- owner-withdrawn account, every one of the account's own statements predates the owner's
-- withdrawal, so testing only at those moments checks the owner branch exactly where it
-- cannot fire. T also ranges over every withdrawal moment of every customer the account has
-- ever been owned by.
--
-- "the account has an as-of answer at T" is account_has_statement_by_t AND NOT
-- account_withdrawn_by_t AND NOT owner_withdrawn_by_t: per
-- inv.account_asof_has_unique_answer, an owner withdrawal at or before T removes the
-- account's own as-of answer at T just as the account's own withdrawal does, so a T where
-- the owner is withdrawn is a T where the account itself has NO as-of answer -- the
-- precondition must exclude it, or this audit asserts the account has an answer while the
-- correctly-projected model says it does not, and fires on data inv.account_single_current
-- and inv.account_asof_has_unique_answer both already accept. This is the reversal of the
-- last review's fault: the account's own withdrawn-owner outcome is a fact about
-- inv.account_asof_has_unique_answer's own coverage, not something this pairing check gets
-- to relitigate by asserting the account still has an answer to pair.
--
-- Consequence, stated rather than hidden: with the owner-withdrawal foreclosure in the
-- precondition, the assertion's own "owner withdrawn at or before T" disjunct below can
-- never fire -- the rows it would fire on are exactly the rows the precondition now
-- excludes. This audit checks the null-owner case and the owner-not-yet-existing case
-- substantively; it checks the owner-withdrawn case only vacuously. That is the honest
-- outcome of a projection that materializes statements, not as-of answers as of an
-- arbitrary T: the withdrawn-owner cascade is produced and checked elsewhere
-- (logical.account.is_current's owner-cascade branch and
-- inv.account_asof_has_unique_answer's own owner branch), and this invariant's own
-- necessity says as much -- it is the cross-entity pairing check, not the cascade's source.
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
),
account_asof_with_owner AS (
  SELECT
    aa.*,
    -- owner_at_t withdrawn at or before T: per inv.account_asof_has_unique_answer, this
    -- alone already removes the account's own as-of answer at T.
    aa.owner_at_t IS NOT NULL AND EXISTS (
      SELECT 1
      FROM customer_withdrawal_bound AS cw
      WHERE cw.customer_number = aa.owner_at_t
        AND cw.first_withdrawal_from <= aa.t
    ) AS owner_withdrawn_by_t
  FROM account_asof AS aa
)
SELECT
  aw.account_number,
  aw.t
FROM account_asof_with_owner AS aw
WHERE aw.account_has_statement_by_t
  AND NOT aw.account_withdrawn_by_t
  AND NOT aw.owner_withdrawn_by_t
  AND (
    aw.owner_at_t IS NULL
    OR aw.owner_withdrawn_by_t
    OR NOT EXISTS (
      SELECT 1
      FROM governed.customer AS c
      WHERE c.customer_number = aw.owner_at_t
        AND c.effective_from <= aw.t
    )
  );
