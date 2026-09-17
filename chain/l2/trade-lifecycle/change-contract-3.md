# Change contract, cycle 3: L1 -> L2, job trade-lifecycle

- **Prior policy authority:** `sketches/l1-brokerage-intent-v1.md`, the clauses listed for `job:trade-lifecycle`.
- **Exact active change authority:** none new at L1. Anchor changes under the data-architect hat: (a) the gate's cross-job type check now compares meaning and physical type only, so a value that is `per_statement` upstream may be `frozen_from_first_encounter` on the trade; (b) `chain/anchors/sources-v1.json` now states `trade_code_meanings` (status codes PNDG, SBMT, CMPT, CNCL, their lifecycle order, terminal codes, and cdc_flag meanings) as source facts. Review findings from the first full review are appended below when it lands.
- **Authorized corrections from the anchor changes:** retype `owning_account_effective_from` and `owning_customer_number` on `logical.trade` as `frozen_from_first_encounter`, citing `L1.attribution-at-placement` (they are the ownership reference fixed at placement); keep their semantic_kind and physical type matching the upstream types. Derive `first_seen_late` from `L1.placement-moment` using the anchored status order: a trade whose first-encountered report carries a status later than the first in the lifecycle order (SBMT for a trade never seen pending, CMPT or CNCL for a trade never seen submitted) is first seen late; if the model cannot state this without inventing beyond the anchored order, file the question.
- **Current rules that must be preserved:** all clauses; cycle-2 elements stand unless corrected here.
- **Explicit holes that must remain open:** unchanged; cdc_flag D stays `L1.hole.deletions`.
- **Retained behavior that must not regress:** outcome attributes mutable with latest_change; placement from the earliest held report's own t_dts; no re-resolution from the current account statement.
- **Stable projection contracts:** unchanged.
- **Forbidden shortcuts / conflict protocol:** unchanged.

## Review findings (review-2.md), all authorized as projection-defect corrections

1. Retype `trade_owning_account_effective_from` and `trade_owning_customer_reference` to `frozen_from_first_encounter`, `history_role: none`, deriving the role from L1.lifecycle-mutates-outcome ("leaves the ownership as first recorded") and L1.attribution-at-placement; remove the "matching the upstream type" sentences; keep semantic_kind and physical type equal to the upstream types; add the cited clauses to `sg.placement-moment.parent_clauses`.
2. `sg.placement-moment`: mode conditional; gap names L1.hole.change-effective-time (pin against deferred upstream statements), L1.hole.batch-identity (whether reports carry which file delivered them), L1.hole.closed-account-activity (a pin landing on a closed-account statement). Strike "per this cycle's authority".
3. Add `first_seen_late` as an attribute with its type. With the anchored `trade_code_meanings.status_order` and `report_order` you may now derive it as a candidate: the first-encountered report's status is later than PNDG in the lifecycle order (SBMT for a trade never seen pending; CMPT or CNCL for a trade never seen submitted). If you judge the anchored order insufficient, declare it deferred and file the question.
4. `hole.batch_identity`: withdraw the dismissal; it bounds `first_encounter_only` and `latest_change` insofar as reports would need to carry their delivery. The selectors themselves now rest on the anchored `report_order` (file production order), which you cite.
5. `sg.outcome`: gap names L1.hole.deletions; `hole.deletions.blocks` lists sg.outcome and sg.placement-moment; cite the anchored cdc_flag meanings for I and U; D stays the hole and latest_change must exclude D rows or be declared blocked by the hole (state which, from the clause text; if neither follows, file the question).
6. `sg.constructed-scenarios`: replace the "references, not copies" premise with reachability through the frozen (owning_account_number, owning_account_effective_from) pair to the upstream statement's provenance; add a deterministic invariant that makes that checkable; make `inv.trade_not_constructed` a data predicate or drop deterministic.

Also: record L1.hole.owner-change-reversions-account, whose resolution would change which account statement placed_at pins.

