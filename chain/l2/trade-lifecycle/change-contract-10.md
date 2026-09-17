# Change contract, cycle 10: L1 -> L2, job trade-lifecycle (text consistency after cycle 9)

- **Prior policy authority:** unchanged (`sketches/l1-brokerage-intent-v1.md`, the clauses for `job:trade-lifecycle`; `selected-model.json` at cycle 9).
- **Exact active change authority:** none new. Text correction authorized by `chain/l3/duckdb-native/trade-lifecycle/review-4.md` (coordinator notes): `inv.every_received_trade_persisted.necessity` still carries the parenthetical "raw.trade_cdc (excluding cdc_flag D reports, per L1.hole.deletions)", which reads as the per-report exclusion review 8 rejected, while the statement and parallel_assumption state the whole-trade exclusion.
- **Authorized correction:** rewrite that parenthetical (and any other sentence in the same element's necessity that implies a per-report exclusion) to the whole-trade reading: a trade_number with any cdc_flag D report is not claimed. No other field of any element moves.
- **Current rules that must be preserved:** all clauses; every cycle-9 element stands unchanged except the one necessity text.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check trade-lifecycle` ok; diff against `selected-model.json` confined to `inv.every_received_trade_persisted.necessity`.
