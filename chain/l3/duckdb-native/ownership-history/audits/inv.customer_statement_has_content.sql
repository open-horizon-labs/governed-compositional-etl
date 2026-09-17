-- inv.customer_statement_has_content: every statement of a customer that is
-- sourced from a feed supplying its own standing facts carries a non-null
-- status and a non-null tier. raw.customer_mgmt_action is the only selected
-- source and it supplies both directly (tier from c_tier; status entailed
-- from action_type), so no governed.customer statement should be missing
-- either. Zero rows means the invariant holds.

SELECT customer_number, effective_from
FROM governed.customer
WHERE status IS NULL OR tier IS NULL;
