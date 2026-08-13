---
id: raw-and-target-model-underdetermine-etl
title: "Raw data and a target model underdetermine ETL semantics"
outcome: governed-compositional-etl-repair
---

Raw values and a destination schema can establish types, shapes, keys, and some structural constraints. They do not establish business meanings such as percentage representation, event-time precedence, identity resolution, slowly changing dimension policy, sign conventions, or the treatment of unseen status codes.

This is not missing compiler sophistication. It is missing authority. The open-world experiment must keep those choices as Sketch holes and use reviewed counterexamples to authorize the smallest general rules needed to resolve them.
