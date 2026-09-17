# Counterfactual round 2: Developer report (before independent review)

Gate: question, zero problems. Both entities content-free by design (identity, effective time, current flag; the account carries its owner reference under L1.owner-standing). One rejected step recorded: decoding ACTV/INAC, tier, and tax status into statement content, rejected because no clause entails that a statement carries it. One question filed: whether a customer or account statement carries any business content beyond identity, effective time, and current flag, and under which clause. Holes carried with honest blocks. No field-name derivations.

Difference from round 1: the anchors no longer license "a statement's status", no longer name the removed clause, and the format makes filing the cheap path and asks for rejected entries. Same Sketch, same job, different Developer behavior.

Gate quirk found by the Developer: the frozen-role clause check applied to rejected steps, so a rejected frozen derivation could not be recorded. Fixed: rejected steps are exempt from that check.
