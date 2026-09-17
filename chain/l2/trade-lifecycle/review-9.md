# Review 9 (coordinator, bookkeeping): job trade-lifecycle (verdict: pass)

Scope: cycle 9 under `change-contract-9.md`, the five corrections review 8 prescribed. Element-level diff against `selected-model.json` (cycle 7): two invariants added; `inv.every_received_trade_persisted` now quantifies over trade_numbers none of whose reports carries D and leaves any D-touched trade to L1.hole.deletions by name, its parallel_assumption cites the anchor's report_order note for the trade_history clause and its review_trigger names a th_t_id with no t_id row; feedback changed on the four pin attributes, trade_number, the two as-of handoffs, the same-statement owner handoff review 8 found missing, and the t_id handoff; review_trigger clauses on the four pin attributes; `sg.placement-moment` members and coverage claim; `sg.trade-identity` members, coverage claim (completeness as well as consistency) and gap naming L1.hole.deletions; `hole.change_effective_time` question; `hole.deletions.blocks`. Nothing else moved. Gate ok, zero problems.

Reviewer: coordinator acting as sketch reviewer for a cycle whose every line the prior review prescribed. Review 8's findings stand as the record.

Rejected element ids: none. Selected: cycles 8 and 9 together.
