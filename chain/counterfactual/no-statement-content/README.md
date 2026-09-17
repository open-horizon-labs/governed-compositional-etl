# Counterfactual: L1 without L1.statement-content and L1.omitted-facts-stand

Sketch-sufficiency test (CESS step 11 and the solution space's success signal 2). A fresh Developer compiles ownership-history from this Sketch, with the same anchors and gate, into `l2/ownership-history/`. Expected: the Developer files a question about what a statement carries and derives no standing attributes from field names; the gate's content rule reports content-free statements. If instead the Developer derives tier, tax treatment, and status from the anchored fields, the compiled model is drawing policy from anchors and the format or contract must tighten.

Run the gate with: CHAIN_L1=chain/counterfactual/no-statement-content/l1-brokerage-intent-counterfactual.md CHAIN_L2_DIR=chain/counterfactual/no-statement-content/l2 .venv/bin/python scripts/chain_l2.py check ownership-history
