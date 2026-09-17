# Change contract, cycle 7: L1 -> L2, job ownership-history

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:ownership-history`, now including `L1.omitted-facts-stand`.
- **Exact active change authority:** approved CE `chain/ce/accepted/ce.l1.omitted-facts-stand.md` and its clause `L1.omitted-facts-stand` (assumed). Plus the text repairs `review-6.md` authorizes.
- **Approved outputs covered by that authority:** every carry-forward derivation (owning_customer_number, tier, tax_treatment) now cites `L1.omitted-facts-stand` as the clause that makes the carried value the statement's value; identity and history remain cited for sameness of subject and kept history.
- **Authorized text repairs:** `sg.statement-content.coverage_claim` states the mechanism per source honestly: direct handoff where the action carries the field, carry-forward where it omits it, naming which actions omit which fields; the two content invariants' `parallel_assumption` say the same; their `statement` and `necessity` drop the "sourced from a feed supplying its own standing facts" hedge and hold unconditionally for candidate-sourced statements; the tier and tax_treatment `derivation.rule` add why a preceding statement exists (the anchored code meanings presuppose an existing customer or account) and their `parallel_assumption` records that predecessor projectability depends on CDC content handoffs staying deferred under L1.hole.change-effective-time.
- **Current rules that must be preserved:** all clauses; cycles 2 to 6 stand.
- **Explicit holes that must remain open:** unchanged.
- **Retained behavior that must not regress:** everything review-5 listed; the cycle-6 derivations.
- **Stable projection contracts:** unchanged. The anchors' fields_present note is shape only.
- **Forbidden shortcuts / conflict protocol:** unchanged.
