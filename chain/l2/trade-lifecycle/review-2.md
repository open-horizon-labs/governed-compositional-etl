# Sketch review 2 (first full review): job trade-lifecycle (verdict: fail)

Reviewer: Opus judge, given S, K, the two change contracts, the upstream model and its review, and the model.

1. `trade_owning_account_effective_from` and `trade_owning_customer_reference` carry `per_statement` (inherited from the upstream type because the gate then demanded an identical role); the entity is incremental_by_identity and the job lists no kept-history clause; the model's own grain and invariant say frozen. Would teach L3 to version trade rows. Gate cause fixed (meaning and physical type only); retype to frozen_from_first_encounter under L1.lifecycle-mutates-outcome.
2. `sg.placement-moment` claims gap none while `hole.change_effective_time` blocks it and the parallel assumption concedes the pin is not resolvable against deferred upstream statements. Mode conditional; gap names the holes.
3. `first_seen_late` dropped as a note and attributed to authority that authorized it. Declare it as a deferred element citing the blocking question or hole; do not resolve by omission.
4. `hole.batch_identity` dismissed while `first_encounter_only` and `latest_change` rely on an ordering of reports the anchors did not state. Anchors now state `report_order` as file production order; the hole stays open about carrying batch identity.
5. `sg.outcome` gap none does not survive L1.hole.deletions: a deletion-marked row would be an ordinary later report under latest_change. Anchors now state cdc_flag meanings; D remains the hole; the hole blocks sg.outcome.
6. `sg.constructed-scenarios` rests on a false premise (the ownership attributes are copies, not references); the reachability argument through the frozen (account_number, effective_from) pair is the right one and needs a checkable invariant; `inv.trade_not_constructed` is a meta-claim, not a data predicate.

Holds: placed_at from the first-encountered report's own t_dts; six outcome facts mutable with latest_change; no invented code meanings; no engine, SQL, table, or file names; roles on types; every clause grouped; derivations subset of parents.
