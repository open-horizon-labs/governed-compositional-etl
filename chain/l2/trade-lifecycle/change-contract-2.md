# Change contract, cycle 2: L1 -> L2, job trade-lifecycle

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:trade-lifecycle`.
- **Exact active change authority:** new clause `L1.placement-moment` (assumed, pending business confirmation), which answers your filed question. Placement is the moment stated by the earliest report of the trade the brokerage holds (its own recorded time, `t_dts`, not the batch date); a trade first seen through a later report is placed at that report's time and marked first-seen-late.
- **Approved outputs covered by that authority:** ownership resolves to the account statement as of the placement moment (the upstream `logical.account` statement whose effective_from is the latest at or before that moment), recorded at first encounter and frozen; through it the customer statement (`logical.account.owning_customer_number` and the customer statement as of the same moment). A first-seen-late marker attribute is authorized. `placed_at` is a frozen attribute carrying the placement moment.
- **Current rules that must be preserved:** all clauses; your cycle-1 elements stand unless this authority changes them.
- **Explicit holes that must remain open:** L1.hole.trade-timestamps now covers completion only; carry it. All others unchanged.
- **Retained behavior that must not regress:** outcome attributes mutable with selector latest_change; owning account frozen; no re-resolution from the current statement.
- **Stable projection contracts:** unchanged.
- **Forbidden shortcuts / conflict protocol:** unchanged. Clear the filed question.
