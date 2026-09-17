### CE: ce.k.account-action-uniqueness

- Status: proposed
- Level: K (anchors), observed at L3 review of ownership-history cycle 3 on both engines
- Input and simulation context: `raw.customer_mgmt_action` declares `(action_ts, c_id)` as its identifier. Account statements are produced per `(ca_id, action_ts)`, and the five value-correctness audits join a statement to its producing action by that pair. Two account-subject actions for one `ca_id` at one `action_ts` with different `c_id` values are identifier-legal.
- Projection output: on such input the account status audit passes when both rows agree on status, and the tax and owner audits inherit the entity SQL's tie nondeterminism in `LAST_VALUE` over a tied order, so they can pass or fail arbitrarily. The duplicate statements themselves are caught by `inv.account_statements_no_overlap` and `inv.account_asof_has_unique_answer`, under those names.
- Corrected output or behavior: either the anchor declares `(ca_id, action_ts)` unique for account-subject actions, so the join is licensed by a stated identity, or the L2 carries a deterministic invariant that at most one account-subject action exists per `(ca_id, action_ts)`, so the collision fires under its own name before any value audit runs.
- Classification: anchor gap; "unique in practice" is load-bearing for three audits and the carry-forward window and nothing states it.
- Proposed generalized change: anchor amendment to `sources-v1.json` entity `raw.customer_mgmt_action` adding a second identity for account-subject rows, with the TPC-DI generator's behavior as the evidence; otherwise an L2 invariant in ownership-history's `sg.identity`.
- Adjacent behavior not authorized: a tie-break rule for colliding actions (which one produces the statement) is business policy and stays open.
- Tempting wrong repair: ordering ties by `c_id` or by file position to make the window deterministic; that decides which customer owns the account by an accident of the file.
- Deterministic assertion: with the invariant, a fixture carrying two account actions at one timestamp yields exactly one violation naming the pair.
- Proposed by: sketch reviewers (Opus), ownership-history L3 cycle-3 reviews on duckdb-native and duckdb-sqlmesh; filed by coordinator.
- Approved or rejected by: pending, anchor authority.
