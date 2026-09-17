-- inv.trade_ownership_provenance_reachable: for any trade_number whose
-- (owning_account_number, owning_account_effective_from) pair resolves, that
-- pair must identify exactly one statement of ownership-history's
-- governed.account entity (so that statement's own provenance value stays
-- reachable through the pair, without this job needing a trade-level
-- provenance attribute of its own). Zero rows means the invariant holds: every
-- trade whose pin is non-null matches exactly one governed.account statement.

SELECT t.trade_number, COUNT(a.account_number) AS matching_statements
FROM governed.trade AS t
LEFT JOIN governed.account AS a
  ON a.account_number = t.owning_account_number
 AND a.effective_from = t.owning_account_effective_from
WHERE t.owning_account_number IS NOT NULL
  AND t.owning_account_effective_from IS NOT NULL
GROUP BY t.trade_number
HAVING COUNT(a.account_number) <> 1;
