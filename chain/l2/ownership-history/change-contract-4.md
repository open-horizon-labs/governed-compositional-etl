# Change contract, cycle 4: L1 -> L2, job ownership-history

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:ownership-history`.
- **Exact active change authority:** none new. Projection-defect corrections authorized by `review-3.md` under the current Sketch and the anchored `action_type_meanings` (now with `subjects` per code).
- **Authorized corrections:** in the account identity handoff and the account owner handoff, enumerate account actions as exactly {NEW, ADDACCT, UPDACCT, CLOSEACCT}, state that INACT and UPDCUST are customer changes that yield no account statement, and that whether they should is L1.hole.owner-change-reversions-account; in the customer identity handoff, enumerate {NEW, UPDCUST, INACT}; add a review trigger for an INACT or UPDCUST row claimed to require an account statement; in the carried-forward owner rule, say what happens when a constructed change is the account's first statement (no previous statement: the owner cannot be carried; file that as a question if no clause settles it).
- **Current rules that must be preserved:** all clauses; cycles 2 and 3 stand.
- **Explicit holes that must remain open:** unchanged.
- **Retained behavior that must not regress:** everything review-3 listed as holding.
- **Stable projection contracts:** unchanged. The gate now checks that action-code enumerations agree per entity and match the anchored subjects.
- **Forbidden shortcuts / conflict protocol:** unchanged.
