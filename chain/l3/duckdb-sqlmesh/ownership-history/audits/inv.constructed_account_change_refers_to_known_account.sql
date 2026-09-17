AUDIT (name inv.constructed_account_change_refers_to_known_account);

-- Every account statement sourced from the labeled constructed scenario ce.account_changes
-- (provenance IS NOT NULL) names an account_number that already has an earlier statement
-- sourced from received records (provenance IS NULL); a constructed change never
-- introduces an account the brokerage does not have.
SELECT
  c.account_number,
  c.effective_from
FROM @this_model AS c
WHERE c.provenance IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM @this_model AS r
    WHERE r.account_number = c.account_number
      AND r.provenance IS NULL
      AND r.effective_from < c.effective_from
  );
