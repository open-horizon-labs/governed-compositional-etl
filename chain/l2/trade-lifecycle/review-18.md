# Review 18 (coordinator, bookkeeping): job trade-lifecycle (verdict: pass)

Scope: cycle 18 under `change-contract-18.md`, compiled from the business's answer to `L1.hole.market-order-seen-pending`. Element-level diff against `selected-model.json` (cycle 17): the carried hole removed with every citation; `inv.trade_market_order_seen_pending_held` deleted and unlisted; `first_seen_late`'s rule restated (a market order is late only above SBMT; PNDG and SBMT are both opening events for one); `inv.trade_first_seen_late_matches_status_order` now claims the case it used to exclude; `inv.trade_first_seen_late_defined_or_held`'s held set shrunk to the unknown-code case; two coverage claims record the closure. `L1.hole.held-first-report-placement` and everything deferring to it untouched. Gate ok, zero problems, invariants 14 to 13.

Note on scope: the Developer also edited `inv.unknown_codes_held` and `sg.unknown-codes.coverage_claim` to drop references to the closed hole. That is inside item 1 ("every citation of it"), and neither edit moves a fingerprint, since element text and coverage claims are not fingerprint material. Accepted.

Reviewer: coordinator acting as sketch reviewer for a cycle whose every line the contract prescribed from a business answer. Rejected element ids: none.
