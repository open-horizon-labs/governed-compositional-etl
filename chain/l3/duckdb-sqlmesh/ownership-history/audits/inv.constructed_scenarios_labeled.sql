AUDIT (name inv.constructed_scenarios_labeled);

-- Every account statement whose source is a labeled constructed scenario carries a
-- non-null, non-blank provenance value. By construction (models/account.sql), provenance
-- is populated only from ce.account_changes.provenance and is otherwise NULL, so a
-- non-null-but-blank label is the one violation this check can observe from @this_model.
SELECT
  account_number,
  effective_from,
  provenance
FROM @this_model
WHERE provenance IS NOT NULL AND TRIM(provenance) = '';
