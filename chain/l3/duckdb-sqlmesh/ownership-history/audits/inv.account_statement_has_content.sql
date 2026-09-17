AUDIT (name inv.account_statement_has_content);

-- Every candidate-sourced statement of an account carries a non-null status and a
-- non-null tax_treatment; a statement missing either is content-free and fails
-- L1.statement-content.
SELECT
  account_number,
  effective_from
FROM @this_model
WHERE status IS NULL OR tax_treatment IS NULL;
