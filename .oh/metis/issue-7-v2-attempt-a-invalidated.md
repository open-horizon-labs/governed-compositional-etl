---
id: issue-7-v2-attempt-a-invalidated
status: accepted-learning
owner_hat: research-sponsor
---

# V2 attempt A invalidated

The research-sponsor hat invalidates v2 attempt A in full. Although each disposable database was hash-verified immediately after copying the frozen start database, the retained trace recorded the database digest after execution. The independent envelope verifier correctly rejected that value as proof of identical starting conditions.

No score, numerator, denominator, threshold evaluation, held-out aggregate, or adoption signal from attempt A counts. The failure is a harness-evidence defect rather than evidence about the compositional method. The corrected attempt must rotate the sealed corpus and nonce, freeze changed harness and custody commitments in a new antecedent commit, record the start digest before any execution, and pass the independent verifier unchanged.
