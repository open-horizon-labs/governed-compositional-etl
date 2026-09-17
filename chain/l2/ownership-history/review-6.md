# Sketch review 6 (scoped): job ownership-history (verdict: fail, text repairs)

Reviewer: Opus judge, scoped to the elements cycle 6 changed and their group; confirmed by byte comparison that nothing else changed since review-5.

Accepted in substance: the carry-forward derivations on tier and tax_treatment, conditioned correctly on the producing action omitting the field.

Defects (projection defects, text): sg.statement-content's coverage claim still explains coverage by direct handoffs and names INACT and CLOSEACCT as producing actions for fields they omit; the two content invariants' parallel assumptions say the same; the invariant statements keep a hedge ("sourced from a feed supplying its own standing facts") that L3 enforced unconditionally; the two carry-forward rules lack the owner rule's third sentence saying why a preceding statement is guaranteed to exist (the anchored code meanings presuppose an existing customer or account) and should record that predecessor projectability depends on CDC content handoffs staying deferred.

Governance finding, accepted: the sentence "absent fields are not changes; the fact stands as last stated" had migrated into an anchor note and the format. Promoted to `L1.omitted-facts-stand` (assumed); anchors scrubbed to shape only. The reviewer's preference for the explicit clause over the entailment is now the Sketch's position.
