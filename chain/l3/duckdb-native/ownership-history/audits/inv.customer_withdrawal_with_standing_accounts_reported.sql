-- inv.customer_withdrawal_with_standing_accounts_reported: reports rather
-- than holds (see DEVELOPER-CONTRACT-L2-L3.md, "An invariant that reports
-- rather than holds"). When a customer statement is a withdrawal
-- (is_withdrawal = true) and one or more accounts have that customer as
-- their owning_customer_number and would otherwise carry a standing at or
-- after the withdrawal's effective moment, each such account is reported for
-- review, naming the account, the withdrawn customer, and the withdrawal's
-- effective moment (case_type = 'withdrawn_owner_with_standing_account').
--
-- Two independent inputs can be unresolvable, and each is reported as
-- unevaluable in its own right rather than silently excluded, per this
-- invariant's own second sentence:
--   1. an account's owning_customer_number itself cannot be resolved
--      (case_type = 'unresolvable_owner', unresolvable_input =
--      'owning_customer_number'). governed.account only ever leaves
--      owning_customer_number null for a withdrawal statement of the
--      account itself (see account.sql), which asserts no standing to lose
--      in the first place, so this branch is currently vacuous but is
--      checked directly rather than assumed.
--   2. an account's owning_customer_number is present but names a
--      customer_number with no statement at all in governed.customer, so
--      that customer's is_withdrawal cannot be looked up (case_type =
--      'unresolvable_owner', unresolvable_input = 'owner_is_withdrawal').
--      This is the case a prior cycle of this audit dropped: it read a
--      missing customer as though the customer were not withdrawn, letting
--      the condition pass over it as false instead of reporting the input
--      as unevaluable.
--
-- "Would otherwise carry a standing at or after the withdrawal's effective
-- moment" is read as: the account's own record has not itself ended (its own
-- last statement is not a withdrawal) -- absent the owner cascade, an
-- unwithdrawn account's standing continues indefinitely, so it always
-- reaches and passes any later moment, including the owner's withdrawal.
-- Both unevaluable arms are checked over the same population (each
-- account's own latest, non-self-withdrawn statement), since that is the
-- statement whose standing the owner's withdrawal or unresolvability would
-- bear on.
--
-- This job currently produces no customer statement with is_withdrawal =
-- true (the CDC source that could set it remains deferred), so the first
-- case_type reports zero rows today; that is the correct empty result of an
-- unexercised condition, not a silent pass over an unevaluated one, per the
-- sg.owner-standing gap note. This invariant is deterministic (its rows are
-- computed, not judged) even though it reports rather than blocks.

WITH withdrawn_customers AS (
    SELECT customer_number, effective_from AS withdrawal_effective_from
    FROM governed.customer
    WHERE is_withdrawal
),
account_own_standing AS (
    -- the account's own latest statement, provided it is not itself a
    -- withdrawal: what the account would show absent the owner cascade.
    SELECT a.account_number, a.owning_customer_number
    FROM governed.account a
    WHERE a.effective_from = (
        SELECT MAX(a2.effective_from)
        FROM governed.account a2
        WHERE a2.account_number = a.account_number
    )
    AND NOT a.is_withdrawal
)
SELECT
    'withdrawn_owner_with_standing_account' AS case_type,
    s.account_number,
    w.customer_number AS withdrawn_customer_number,
    w.withdrawal_effective_from,
    CAST(NULL AS VARCHAR) AS unresolvable_input
FROM account_own_standing s
JOIN withdrawn_customers w ON w.customer_number = s.owning_customer_number

UNION ALL

-- unevaluable arm 1: owning_customer_number itself is unresolvable.
SELECT
    'unresolvable_owner' AS case_type,
    a.account_number,
    CAST(NULL AS BIGINT) AS withdrawn_customer_number,
    CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
    'owning_customer_number' AS unresolvable_input
FROM governed.account a
WHERE NOT a.is_withdrawal
  AND a.owning_customer_number IS NULL

UNION ALL

-- unevaluable arm 2: owning_customer_number is resolved, but that customer
-- has no statement at all in governed.customer, so its is_withdrawal cannot
-- be looked up. Not the same population as the withdrawn-owner branch above
-- (which requires a matching customer statement to join against), so this
-- arm reports exactly the accounts the withdrawn-owner branch cannot see.
SELECT
    'unresolvable_owner' AS case_type,
    s.account_number,
    CAST(NULL AS BIGINT) AS withdrawn_customer_number,
    CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
    'owner_is_withdrawal' AS unresolvable_input
FROM account_own_standing s
WHERE s.owning_customer_number IS NOT NULL
  AND NOT EXISTS (
        SELECT 1 FROM governed.customer c
        WHERE c.customer_number = s.owning_customer_number
      );
