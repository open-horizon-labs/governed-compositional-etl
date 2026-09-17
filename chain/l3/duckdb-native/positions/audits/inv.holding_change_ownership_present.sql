-- inv.holding_change_ownership_present: every persisted logical.holding_change
-- row carries owning_account_number, owning_account_effective_from,
-- owning_customer_number, and owning_customer_effective_from non-null.
-- holding_change.sql's CREATE TABLE deliberately declares no NOT NULL (a
-- column constraint would abort the MERGE before this audit ever ran,
-- deciding in the schema a disposition the model reserves for review); this
-- audit is the mechanism that makes the exclusion rule's non-null promise
-- (keep a report only when all four copied values resolve) checkable instead
-- of assumed. Zero rows means the invariant holds.

SELECT
    original_trade_number,
    current_trade_number
FROM governed.holding_change
WHERE owning_account_number IS NULL
   OR owning_account_effective_from IS NULL
   OR owning_customer_number IS NULL
   OR owning_customer_effective_from IS NULL;
