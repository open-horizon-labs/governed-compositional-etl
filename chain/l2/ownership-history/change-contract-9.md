# Change contract, cycle 9: L1 -> L2, job ownership-history

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:ownership-history`.
- **Exact active change authority:** none. Bookkeeping repair under a gate rule mechanized from the trade-lifecycle review: a hole's `blocks` and a group's `gap` must agree in both directions. Review-5 had noted the same ("a second hole id in the gap would be clearer").
- **Authorized corrections:** for each hole that lists a group in `blocks`, that group's `gap` names the hole's L1 id: `sg.owner-standing.gap` adds L1.hole.change-effective-time and L1.hole.deletions; `sg.history-asof.gap`, `sg.current-version.gap`, `sg.statement-content.gap` add L1.hole.deletions. Alternatively, if a hole does not in fact bound a group's members, remove the group from the hole's `blocks` and say why in the hole's question. Choose per hole from the model's own text; do not change any coverage claim's substance.
- **Current rules that must be preserved:** all clauses; cycles 2 to 8 stand. No element other than group `gap` fields and hole `blocks` lists may change.
- **Stable projection contracts / forbidden shortcuts / conflict protocol:** unchanged.
