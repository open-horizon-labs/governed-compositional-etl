-- inv.customer_withdrawal_with_standing_accounts_reported: reports rather
-- than holds (see DEVELOPER-CONTRACT-L2-L3.md, "An invariant that reports
-- rather than holds"). When a customer statement is a withdrawal
-- (is_withdrawal = true) and one or more accounts have that customer as
-- their owning_customer_number and would otherwise carry a standing at or
-- after the withdrawal's effective moment, each such account is reported for
-- review, naming the account, the withdrawn customer, and the withdrawal's
-- effective moment (case_type = 'withdrawn_owner_with_standing_account').
--
-- When an account's owning_customer_number cannot be resolved, that account
-- is reported as unevaluable for this check instead of silently excluded
-- (case_type = 'unresolvable_owner'). governed.account only ever leaves
-- owning_customer_number null for a withdrawal statement of the account
-- itself (see account.sql), which asserts no standing to lose in the first
-- place, so this branch is currently vacuous but is checked directly rather
-- than assumed.
--
-- "Would otherwise carry a standing at or after the withdrawal's effective
-- moment" is read as: the account's own record has not itself ended (its own
-- last statement is not a withdrawal) -- absent the owner cascade, an
-- unwithdrawn account's standing continues indefinitely, so it always
-- reaches and passes any later moment, including the owner's withdrawal.
--
-- This job currently produces no customer statement with is_withdrawal =
-- true (the CDC source that could set it remains deferred), so this audit
-- reports zero rows today; that is the correct empty result of an
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

SELECT
    'unresolvable_owner' AS case_type,
    a.account_number,
    CAST(NULL AS BIGINT) AS withdrawn_customer_number,
    CAST(NULL AS TIMESTAMP) AS withdrawal_effective_from,
    'owning_customer_number' AS unresolvable_input
FROM governed.account a
WHERE NOT a.is_withdrawal
  AND a.owning_customer_number IS NULL;
