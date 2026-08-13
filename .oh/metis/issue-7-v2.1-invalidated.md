---
id: issue-7-v2.1-invalidated
status: accepted-learning
owner_hat: research-sponsor
---

# V2.1 invalidated

The research-sponsor hat invalidates v2.1 in full. The injected edge SQL was planned successfully, but the retained live probe read the previously promoted clean `governed.dim_trade` table rather than a materialization produced from the injected projection. The retained evidence therefore did not demonstrate the corrupted downstream value that the repair claimed to correct.

No v2.1 score, numerator, denominator, threshold evaluation, held-out aggregate, or adoption signal counts. The next attempt must materialize every injected and repaired projection into explicitly named experiment tables, retain the before/after live values, derive affected descendants from the governed change profile rather than scorer truth, rotate custody and nonce, freeze exact changes in a new antecedent, and pass an unchanged independent verifier.
