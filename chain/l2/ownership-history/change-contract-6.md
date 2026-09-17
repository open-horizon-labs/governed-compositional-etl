# Change contract, cycle 6: L1 -> L2, job ownership-history

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:ownership-history`. Unchanged.
- **Exact active change authority:** none. This is an implementation repair of the L2 model under the existing clauses, adjudicated in `adjudication-l3-sim-1.md`. Anchor fact added under the data-architect hat: `action_type_meanings.fields_present` in `chain/anchors/sources-v1.json`.
- **Authorized correction:** on `logical.customer.tier` and `logical.account.tax_treatment`, declare `derivation` {kind carried_forward_from_previous_statement, rule: the fact stands as last stated when the producing action omits it}, citing L1.identity, L1.history, and L1.statement-content, as the owner attribute already does. Keep the direct handoffs; the derivation covers the omitted case. Adjust necessity, parallel assumption, and review trigger to say so. Extend group parents if the subset rule requires. Do not touch `status`: every producing action determines it.
- **Current rules that must be preserved:** all clauses; cycles 2 to 5 stand.
- **Explicit holes that must remain open:** unchanged.
- **Retained behavior that must not regress:** everything review-5 listed.
- **Stable projection contracts:** unchanged. The gate now rejects a non-nullable statement attribute handed off from a field that a producing action omits, unless it carries forward or is nullable.
- **Forbidden shortcuts / conflict protocol:** unchanged.
