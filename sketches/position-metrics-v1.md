---
id: position-metrics-v1
status: incomplete
owner_hat: data-product-owner
authority: sketch-level path invariant over governed FactHoldings
chain_position: 5
depends_on: fact-holdings-v1
---

# Position metrics Sketch v1

Governs the end-to-end invariant: positions by account version and by customer version. It is intentionally incomplete.

## Known rules in order

1. **Position is the sum of quantity deltas.** For each dimension version, position = sum(after_quantity - before_quantity) over FactHoldings rows carrying that version's key.
2. **A dimension version never holds a negative position.** A negative value means a lot was opened under one version and closed under another. That is exactly what a rebound key produces while every foreign key stays valid. Deterministic gates `position_by_account.nonnegative` and `position_by_customer.nonnegative`.
3. **Verify twice.** Gates, then review against this Sketch.

## Explicit holes

| Hole | Question | Owner hat | Permitted resolution | Forbidden shortcuts |
|---|---|---|---|---|
| `metrics.security-dimension` | Should position be by security as well? | data-product owner | Named rule once DimSecurity enters | Grouping by the raw symbol |

## Artifact and authority separation

Metrics are projections of governed facts. They may not be repaired directly; every repair authority in this chain forbids `metric.position_by_account` and `metric.position_by_customer`.
