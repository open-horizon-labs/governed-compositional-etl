AUDIT (name "inv.trade_ownership_provenance_reachable");

-- For any trade_number whose (owning_account_number, owning_account_effective_from) pair
-- resolves, that pair identifies exactly one statement of ownership-history's logical.account
-- entity, and that statement's own provenance value is the provenance reachable for this
-- trade. Zero or more than one matching governed.account statement is a violation.
SELECT
  m.trade_number
FROM @this_model AS m
LEFT JOIN governed.account AS a
  ON a.account_number = m.owning_account_number
 AND a.effective_from = m.owning_account_effective_from
GROUP BY m.trade_number
HAVING COUNT(a.account_number) <> 1;
