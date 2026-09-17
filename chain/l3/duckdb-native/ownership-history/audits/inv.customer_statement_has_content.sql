-- inv.customer_statement_has_content: every candidate-sourced statement of a
-- customer carries a non-null status and a non-null tier; a versioned
-- statement without either is content-free and fails L1.statement-content.
-- Holds unconditionally for raw.customer_mgmt_action-sourced statements: NEW
-- and UPDCUST carry c_tier directly; INACT omits it, so tier is carried
-- forward from the customer's preceding statement under L1.omitted-facts-stand;
-- status is entailed by the anchored action_type meaning on every one of NEW,
-- UPDCUST, INACT. Zero rows means the invariant holds.

SELECT customer_number, effective_from
FROM governed.customer
WHERE status IS NULL OR tier IS NULL;
