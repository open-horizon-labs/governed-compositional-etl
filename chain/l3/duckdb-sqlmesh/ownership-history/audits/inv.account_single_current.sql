AUDIT (name "inv.account_single_current");

-- For any account_number, at most one statement has is_current = true, always. If the
-- account's own record still stands (no statement of that account is a withdrawal) and its
-- owning customer still stands (the owning customer carries no withdrawal statement at all,
-- at any moment, per L1.owner-standing's extended second sentence), exactly one is current;
-- if either condition fails, none is current.
--
-- is_current can only ever be true for the account's latest-dated statement(s) (the model's
-- fallback branch requires "no statement of the same account_number has a later
-- effective_from", which every tied-latest statement satisfies equally, so the model's own
-- ELSE arm marks ALL of them current, not one), so the owner condition must be evaluated
-- against the owning_customer_number named by that latest moment, not against every
-- owning_customer_number the account has ever carried: an account whose owner changed from
-- a withdrawn C1 to a standing C2 has its latest statement owned by C2, and is correctly
-- current, even though an earlier statement named a withdrawn owner. Collapsing the owner
-- check to "any statement's owner was ever withdrawn" would fire on that account for
-- behavior the model requires. Own-withdrawal, by contrast, is correctly evaluated over
-- every statement of the account: a withdrawal anywhere in the account's own history
-- forecloses currency for every later statement, including its latest one, per the
-- reversal-foreclosure branch.
--
-- ROW_NUMBER() needs an explicit tiebreak: two statements of one account at the same
-- effective_from are producible (unioned is a bare UNION ALL of the raw and constructed
-- arms with no dedupe, and no anchored source forbids it), and on an unbroken tie
-- rn = 1's pick is unspecified -- if the tied statements name different owners with one
-- withdrawn, the verdict flips with the pick. Not blocking, because a tie independently
-- violates inv.account_statements_no_overlap and inv.account_asof_has_unique_answer, so no
-- tied data reaches acceptance regardless; the tiebreak is added anyway so this audit's own
-- verdict does not depend on an unspecified pick even transiently.
WITH owner_withdrawn_customers AS (
  SELECT DISTINCT customer_number
  FROM governed.customer
  WHERE is_withdrawal
),
latest_statement AS (
  SELECT
    account_number,
    owning_customer_number,
    ROW_NUMBER() OVER (
      PARTITION BY account_number
      ORDER BY effective_from DESC, owning_customer_number DESC NULLS LAST,
        status DESC NULLS LAST, tax_treatment DESC NULLS LAST, provenance DESC NULLS LAST
    ) AS rn
  FROM @this_model
),
flags AS (
  SELECT
    a.account_number,
    SUM(CASE WHEN a.is_current THEN 1 ELSE 0 END) AS current_count,
    MAX(CASE WHEN a.is_withdrawal THEN 1 ELSE 0 END) AS own_withdrawn
  FROM @this_model AS a
  GROUP BY a.account_number
),
owner_flags AS (
  SELECT
    l.account_number,
    CASE WHEN w.customer_number IS NOT NULL THEN 1 ELSE 0 END AS owner_withdrawn
  FROM latest_statement AS l
  LEFT JOIN owner_withdrawn_customers AS w
    ON w.customer_number = l.owning_customer_number
  WHERE l.rn = 1
)
SELECT f.account_number
FROM flags AS f
JOIN owner_flags AS o
  ON o.account_number = f.account_number
WHERE
  (f.own_withdrawn = 0 AND o.owner_withdrawn = 0 AND f.current_count <> 1)
  OR
  ((f.own_withdrawn = 1 OR o.owner_withdrawn = 1) AND f.current_count <> 0);
