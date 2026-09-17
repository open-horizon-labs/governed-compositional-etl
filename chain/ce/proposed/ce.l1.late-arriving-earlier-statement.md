### CE: ce.l1.late-arriving-earlier-statement

- Status: proposed
- Level: L1, observed at L3 review of trade-lifecycle on duckdb-sqlmesh (audit inv.trade_placement_reference_frozen recomputes the pin against current account statements)
- Input and simulation context: a scratch copy with an account statement for 428 effective 2015-01-01, arriving after trades were pinned to the 2012 statement.
- Projection output: frozen values preserved (correct under L1.attribution-at-placement); the recomputing audit reports both trades.
- Question for the business: when an account statement arrives late but is effective before a trade's placement and after the statement the trade pinned, does the trade re-pin (the new statement is what stood at placement) or does the first recorded pin win (a later change never moves an already placed trade)? L1.attribution-at-placement speaks of later changes; a late-arriving earlier statement is a correction of history, which the clause does not address.
- Tempting wrong repair: weakening the audit to compare only against stored values, which would also hide an is_current mis-pin.
- Proposed by: projection reviewer (Opus).
- Approved or rejected by: pending, business authority.
