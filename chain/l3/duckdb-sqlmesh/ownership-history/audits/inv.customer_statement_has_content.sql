AUDIT (name inv.customer_statement_has_content);

-- Every candidate-sourced statement of a customer carries a non-null status and a
-- non-null tier; a statement missing either is content-free and fails L1.statement-content.
SELECT
  customer_number,
  effective_from
FROM @this_model
WHERE status IS NULL OR tier IS NULL;
