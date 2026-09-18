AUDIT (name "inv.customer_withdrawal_with_standing_accounts_reported", blocking false);

-- L1.deletion-withdraws: when a customer statement is a withdrawal and one or more
-- accounts have that customer as their owning_customer_number and would otherwise carry a
-- standing at or after the withdrawal's effective moment, each such account is reported
-- for review -- because a customer that still owns accounts is one the brokerage may not
-- have meant to withdraw. This reports rather than fails: on this target the audit is
-- declared non-blocking so a returning row is a finding for the business, not a defect in
-- this projection. When an account's owning_customer_number, or the is_withdrawal value of
-- the customer it names, cannot be resolved, that account is reported as unevaluable
-- instead of silently passed over as though the condition were false.
--
-- No candidate source this job reads today can produce a customer statement with
-- is_withdrawal = true (both the customer and account CDC handoffs that could set it
-- remain deferred under L1.hole.change-effective-time), so this audit reports zero rows on
-- the fixture -- the correct empty result of an unexercised condition, not a silent pass.
WITH customer_withdrawals AS (
  SELECT
    customer_number,
    effective_from AS withdrawal_effective_from
  FROM governed.customer
  WHERE is_withdrawal
)
SELECT
  a.account_number,
  cw.customer_number AS withdrawn_customer,
  cw.withdrawal_effective_from,
  'reported: standing account of a withdrawn customer' AS finding
FROM @this_model AS a
JOIN customer_withdrawals AS cw
  ON cw.customer_number = a.owning_customer_number
WHERE a.is_withdrawal = FALSE
  AND a.effective_from >= cw.withdrawal_effective_from
UNION ALL
SELECT
  a.account_number,
  a.owning_customer_number AS withdrawn_customer,
  CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
  'unevaluable: owning_customer_number could not be resolved' AS finding
FROM @this_model AS a
WHERE a.is_withdrawal = FALSE
  AND a.owning_customer_number IS NULL
UNION ALL
SELECT
  a.account_number,
  a.owning_customer_number AS withdrawn_customer,
  CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
  'unevaluable: owning customer''s is_withdrawal could not be resolved' AS finding
FROM @this_model AS a
WHERE a.is_withdrawal = FALSE
  AND a.owning_customer_number IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM governed.customer AS c
    WHERE c.customer_number = a.owning_customer_number
  );
