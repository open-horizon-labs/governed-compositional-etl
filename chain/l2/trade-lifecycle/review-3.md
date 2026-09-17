# Sketch review 3: job trade-lifecycle (verdict: fail, bookkeeping)

Reviewer: Opus judge. Review-2 findings 1, 2, 3, 5, 6 addressed; 4 still open in the groups' gaps.

Defects: hole.batch_identity blocks sg.trade-shape and sg.outcome but sg.trade-shape's gap is none and sg.outcome's gap omits the hole; hole.owner_change_reversions_account blocks sg.placement-moment while that group's claim says it blocks nothing and its gap omits the hole; sg.placement-moment's gap names closed-account-activity while that hole lists no blocks. Secondary: first_seen_late's derivation rests on the unstated premise that every trade's lifecycle begins at PNDG, which the anchored meaning of PNDG (a limit order) contradicts for market orders; state the premise, widen the review trigger, keep the derivation as a review flag. Smaller: trade_owning_account_reference should also cite L1.lifecycle-mutates-outcome; trade_first_seen_late history_role none; move the meta-claim out of inv.trade_ownership_provenance_reachable's statement; sg.constructed-scenarios gap should name change-effective-time or scope its claim; hole.deletions should label the current D-handling as provisional.

Possible sketch gap (filed, not decided): how the brokerage distinguishes a trade first seen late from a market order whose life legitimately begins at submitted.

Mechanized: holes' blocks and groups' gaps must agree in both directions.
