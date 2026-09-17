AUDIT (name "inv.constructed_scenarios_labeled");

-- Every account statement whose source is a labeled constructed scenario carries a
-- non-null provenance value; no account statement sourced from received records carries
-- one. Source is determined by matching @this_model back to ce.account_changes, the
-- entity's declared constructed-scenario read, on (account_id = account_number,
-- action_at = effective_from) -- not by provenance nullness, which is the fact under test.
SELECT
  m.account_number,
  m.effective_from,
  m.provenance
FROM @this_model AS m
JOIN ce.account_changes AS c
  ON c.account_id = m.account_number
  AND c.action_at = m.effective_from
WHERE m.provenance IS NULL OR TRIM(m.provenance) = ''
UNION ALL
SELECT
  m.account_number,
  m.effective_from,
  m.provenance
FROM @this_model AS m
WHERE m.provenance IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM ce.account_changes AS c
    WHERE c.account_id = m.account_number
      AND c.action_at = m.effective_from
  );
