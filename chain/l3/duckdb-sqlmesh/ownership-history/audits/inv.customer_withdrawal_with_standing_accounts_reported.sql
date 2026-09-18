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
-- The population is existence-based, not a date comparison: an account matches when it has
-- ANY non-withdrawal statement naming the withdrawn customer as its owner, with no
-- comparison between the account's own effective_from and the withdrawal's moment. A
-- withdrawal creates no account statement, so an account owned by a withdrawn customer
-- normally has every one of its own statements dated BEFORE the withdrawal -- that is the
-- ordinary shape, not an edge case -- and a date comparison (`account effective_from >=
-- withdrawal effective_from`) would only ever fire for the unusual case of a later,
-- unrelated account statement landing after the withdrawal, missing the ordinary
-- withdrawn-owner population entirely. This is the same form L2 reviews 15 and 16 rejected
-- for logical.account.is_current's owner-cascade branch, and the same form the L2 model
-- resolved to existence there: is_current's owner branch and its own parallel_assumption
-- fire on the mere existence of any owner withdrawal, at any moment, with no comparison to
-- the account's own effective_from, precisely because that comparison can never fire for
-- the population the clause is about (an account with no statement anywhere near its
-- owner's withdrawal). This audit uses the identical existence form for the identical
-- reason.
--
-- Each matching account is reported once, not once per matching statement: a report
-- handed to the business should name the account once, so every branch below selects
-- DISTINCT account_number (or the distinct (account_number, unresolved input) pair for the
-- unevaluable arms) rather than joining per statement.
--
-- No candidate source this job reads today can produce a customer statement with
-- is_withdrawal = true (both the customer and account CDC handoffs that could set it
-- remain deferred under L1.hole.change-effective-time), so this audit reports zero rows on
-- the fixture -- the correct empty result of an unexercised condition, not a silent pass.
WITH customer_withdrawal_bound AS (
  SELECT
    customer_number,
    MIN(effective_from) AS withdrawal_effective_from
  FROM governed.customer
  WHERE is_withdrawal
  GROUP BY customer_number
),
standing_accounts AS (
  SELECT DISTINCT
    a.account_number,
    cw.customer_number AS withdrawn_customer,
    cw.withdrawal_effective_from
  FROM @this_model AS a
  JOIN customer_withdrawal_bound AS cw
    ON cw.customer_number = a.owning_customer_number
  WHERE a.is_withdrawal = FALSE
),
unresolved_owner AS (
  SELECT DISTINCT account_number
  FROM @this_model
  WHERE is_withdrawal = FALSE
    AND owning_customer_number IS NULL
),
unresolved_customer AS (
  SELECT DISTINCT
    a.account_number,
    a.owning_customer_number
  FROM @this_model AS a
  WHERE a.is_withdrawal = FALSE
    AND a.owning_customer_number IS NOT NULL
    AND NOT EXISTS (
      SELECT 1
      FROM governed.customer AS c
      WHERE c.customer_number = a.owning_customer_number
    )
)
SELECT
  account_number,
  withdrawn_customer,
  withdrawal_effective_from,
  'reported: standing account of a withdrawn customer' AS finding
FROM standing_accounts
UNION ALL
SELECT
  account_number,
  CAST(NULL AS BIGINT) AS withdrawn_customer,
  CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
  'unevaluable: owning_customer_number could not be resolved' AS finding
FROM unresolved_owner
UNION ALL
SELECT
  account_number,
  owning_customer_number AS withdrawn_customer,
  CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
  'unevaluable: owning customer''s is_withdrawal could not be resolved' AS finding
FROM unresolved_customer;
