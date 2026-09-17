-- inv.customer_status_matches_producing_source: for every candidate-sourced
-- customer statement produced by a historical action, status equals the
-- interpreted meaning of that action's action_type (NEW, UPDCUST: active;
-- INACT: inactive). sources-v1.json's action_type_meanings state a status
-- only for INACT (the row reports a customer becoming inactive); active for
-- NEW and UPDCUST is not stated there but is the reading recorded in this
-- invariant's parallel_assumption. Expected status is recomputed from
-- raw.customer_mgmt_action (the producing source), joined on
-- (customer_number, effective_from) = (c_id, action_ts), never read back
-- from governed.customer.status. The CASE is exhaustive over the anchored
-- codes and falls to NULL for any other action_type on purpose: a customer
-- statement wrongly produced from an account-subject action at the same
-- (c_id, action_ts) then compares a non-null status against expected NULL
-- and is reported, rather than being filtered out of the join and missed.
-- Zero rows means the invariant holds.

SELECT c.customer_number, c.effective_from
FROM governed.customer c
JOIN raw.customer_mgmt_action r
    ON r.c_id = c.customer_number
   AND r.action_ts = c.effective_from
WHERE c.status IS DISTINCT FROM (
    CASE r.action_type
        WHEN 'NEW'     THEN 'ACTV'
        WHEN 'UPDCUST' THEN 'ACTV'
        WHEN 'INACT'   THEN 'INAC'
    END
);
