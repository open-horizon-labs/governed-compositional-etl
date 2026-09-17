### CE: ce.l1.closed-account-activity

- Status: accepted 2026-09-17 (business authority); clause `L1.closed-account-activity` added, hole `L1.hole.closed-account-activity` closed
- Level: L1, observed in the received records themselves at the first compile of ownership-history
- Input and simulation context: account 428 has a CLOSEACCT statement effective 2012-11-15, and the received trade files report trades 353232 (placed 2017-01-12) and 372101 (placed 2017-04-10) on it. This is not constructed; it is in the TPC-DI SF3 data the chain reads.
- Projection output before the answer: both trades were attributed to account 428's 2012 closing statement and nothing said anything about it. Every audit passed. The chain was silent about a contradiction sitting in its own input.
- Question for the business: is a trade on a closed account a data error, a reopening the records omit, or does a closed account still own trades?
- Answer (business authority, 2026-09-17): a closed account keeps everything it already held, and closing it unwinds nothing. A trade placed after the closing statement is recorded like any other and reported for review, because either the closure or the trade is wrong and only the brokerage can say which. Activity never reopens an account.
- Corrected output or behavior: the two trades are still attributed exactly as before, and the chain now reports them. The report is the point: it is the first thing the chain says back to the business about the business's own records.
- Adjacent behavior not authorized: deciding which of the closure and the trade is wrong; unwinding or re-attributing anything.
- Tempting wrong repair: dropping such trades, reopening the account, or re-pinning the trade to an earlier open statement. All three invent a fact the records do not carry.
- Deterministic assertion: on the received fixture, the report names exactly trades 353232 and 372101 on account 428, on both engines, and no other audit changes.
- Proposed by: coordinator from the received records; hole opened at the first ownership-history compile.
- Approved or rejected by: approved, business authority (2026-09-17).
