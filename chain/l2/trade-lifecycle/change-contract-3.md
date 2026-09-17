# Change contract, cycle 3: L1 -> L2, job trade-lifecycle

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:trade-lifecycle`.
- **Exact active change authority:** none new at L1. Anchor changes under the data-architect hat: (a) the gate's cross-job type check now compares meaning and physical type only, so a value that is `per_statement` upstream may be `frozen_from_first_encounter` on the trade; (b) `chain/anchors/sources-v1.json` now states `trade_code_meanings` (status codes PNDG, SBMT, CMPT, CNCL, their lifecycle order, terminal codes, and cdc_flag meanings) as source facts. Review findings from the first full review are appended below when it lands.
- **Authorized corrections from the anchor changes:** retype `owning_account_effective_from` and `owning_customer_number` on `logical.trade` as `frozen_from_first_encounter`, citing `L1.attribution-at-placement` (they are the ownership reference fixed at placement); keep their semantic_kind and physical type matching the upstream types. Derive `first_seen_late` from `L1.placement-moment` using the anchored status order: a trade whose first-encountered report carries a status later than the first in the lifecycle order (SBMT for a trade never seen pending, CMPT or CNCL for a trade never seen submitted) is first seen late; if the model cannot state this without inventing beyond the anchored order, file the question.
- **Current rules that must be preserved:** all clauses; cycle-2 elements stand unless corrected here.
- **Explicit holes that must remain open:** unchanged; cdc_flag D stays `L1.hole.deletions`.
- **Retained behavior that must not regress:** outcome attributes mutable with latest_change; placement from the earliest held report's own t_dts; no re-resolution from the current account statement.
- **Stable projection contracts:** unchanged.
- **Forbidden shortcuts / conflict protocol:** unchanged.

## Review findings (appended after review)
