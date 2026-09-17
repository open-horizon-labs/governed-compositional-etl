# Change contract, cycle 8: L1 -> L2, job ownership-history

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:ownership-history`.
- **Exact active change authority:** none new. Text repairs authorized by `review-7.md`. This contract corrects contract-7's over-narrow scope on the owner attribute.
- **Authorized corrections:** `logical.account.owning_customer_number`: rewrite `derivation.rule` and `necessity` on the pattern tier and tax_treatment now use: the carry is by `L1.omitted-facts-stand` (a constructed change that does not mention the owner leaves the owner as it last stood); `L1.identity` and `L1.history` are cited only to make "this account's immediately preceding statement" well defined; keep the third sentence (`L1.constructed-scenarios` and `inv.constructed_account_change_refers_to_known_account`) guaranteeing the predecessor exists; delete the sentence "an unstated fact therefore continues from the prior statement unless the new statement itself asserts a change to it". `sg.owner-standing.coverage_claim`: attribute the carry-forward to `L1.omitted-facts-stand`, not to a re-derivation from identity and history.
- **Current rules that must be preserved:** all clauses; cycles 2 to 7 stand.
- **Explicit holes that must remain open:** unchanged.
- **Retained behavior that must not regress:** everything review-5 and review-7 listed as holding.
- **Stable projection contracts:** unchanged.
- **Forbidden shortcuts / conflict protocol:** unchanged.
