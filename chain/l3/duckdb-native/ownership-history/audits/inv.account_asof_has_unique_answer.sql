-- inv.account_asof_has_unique_answer: for any account_number and any moment T,
-- exactly one statement is the latest one effective at or before T, or none if
-- T precedes the first statement. This holds whenever every statement has a
-- determinable (non-null) effective_from and no two statements of the same
-- account_number share an effective_from. Zero rows means the invariant holds.

SELECT account_number
FROM governed.account
GROUP BY account_number
HAVING COUNT(effective_from) <> COUNT(*)
    OR COUNT(DISTINCT effective_from) <> COUNT(*);
