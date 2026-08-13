# Issue #5 Sketch review

**Reviewer hat:** domain reviewer

**Projection:** freshly generated `governed.dim_trade` on the verified issue #2 persistent DuckDB substrate

**Sketch:** `sketches/trade-dim-v1.md`

**Decision:** pass for the bounded historical projection exercised here

## Review

- Trade and TradeHistory remain distinct local stages with their declared grains and identity.
- The lifecycle model joins those stages on `trade_id`.
- Creation time is selected from the `SBMT` history observation for market trades and `PNDG` for the remaining bounded historical path.
- Close time is selected from `CMPT` or `CNCL` history observations.
- Trade ID `0` materializes with creation `2012-07-07T00:01:13`, close `2012-07-07T00:02:34`, status `Completed`, and type `Market Buy`, consistent with the current Sketch and named contracts.
- The logical projection copies the typed lifecycle handoff and resolves the named status and trade-type references.

The open incremental, effective-dated key, batch-ID, and pricing-policy holes remain uncompiled. This review does not fill them.

## Separation from deterministic evidence

SQLMesh audits independently establish non-null trade identities and non-reversed lifecycle timestamps on the materialized corpus. Those green audits did not supply this semantic judgment and do not replace it. This review does not establish correctness outside the current Sketch, slice, and observed corpus.
