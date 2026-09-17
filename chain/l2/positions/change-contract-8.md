# Change contract, cycle 8: L1 -> L2, job positions (unknown codes are held, never interpreted)

- **Prior policy authority:** the previous selection (`selected-model.json`).
- **Exact active change authority:** the Sketch gained clause `L1.unknown-codes` (the brokerage's records speak in a fixed vocabulary of codes; a report carrying a code the vocabulary does not name is held for review and never interpreted, defaulted or dropped; every job reports it as a violation naming the record and the code) and this job now lists it. Cause: `chain/ce/accepted/ce.l1.unknown-codes-held.md`. The weave shows the clause uncovered until you cover it.
- **Authorized additions:**
  1. A deterministic invariant `inv.unknown_codes_held` (one per anchored coded field this job reads: for every source row this job consumes, each coded field carries a value the anchors name, or the row is reported). Name the fields and their anchored vocabularies from `chain/anchors/sources-v1.json` (action_type codes; status_codes; cdc_flag; trade_type_codes; ce.account_changes status_id has no declared vocabulary: say so and leave it a review trigger, do not invent one). The invariant reports; it does not say what happens to the record afterwards.
  2. Every derivation or handoff in this job that reads a coded field: add a sentence to its parallel_assumption that an unknown value is held under L1.unknown-codes and yields no derived fact, and list the new invariant in its feedback.
- **Groups:** a new group \`sg.unknown-codes\` (parent L1.unknown-codes) for item 1. Coverage claims state what is claimed; `gap` names holes as the format requires.
- **Current rules that must be preserved:** everything else; no other hole moves.
- **Conflict protocol reminder:** one question, omit the element, return, if the Sketch or anchors do not carry what an item needs.
- **Acceptance:** `.venv/bin/python scripts/chain_l2.py check positions` ok with zero problems; the weave no longer lists L1.unknown-codes as a gap once all three jobs have compiled; diff confined to the enumerated elements.
