---
id: issue-7-v2.3-invalidated
status: accepted-learning
owner_hat: research-sponsor
---

# V2.3 invalidated

The independent verifier rejected v2.3 because it incorrectly required the edge timestamp to change in every arm. That contradicts the treatment: an arm that cannot see contract evidence must remain inconclusive and retain the materially observed defect, while a resolved proposal must change it. No v2.3 result counts. The verifier must enforce this conditional invariant, custody and nonce must rotate, and a new antecedent must precede another scored run.
