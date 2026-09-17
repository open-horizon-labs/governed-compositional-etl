---
id: l1-brokerage-intent-v1
level: 1
status: incomplete
owner_hat: data-product-owner (business authority)
authority: the brokerage's own statement of what its reporting means; TPC-DI 1.1.0 supplies the source files and natural identities only
---

# What the brokerage needs to know (L1 intent Sketch)

This is the top of the chain. It says what the numbers mean, in the brokerage's language. It does not name tables, keys, SQL, engines, or file layouts. Everything below it is compiled from it and can be thrown away; this document cannot.

Each clause has a stable id and is hashed on its own, so changing one clause invalidates only what derives from it. A clause is a rule the business stands behind. A hole is a question the business has not answered; nothing downstream may answer it by guessing.

## Jobs

Each job compiles to its own semantic model. A job lists the clauses it needs.

- **job:ownership-history** — Know how any customer or account stood at any moment, and who owned what. Clauses: L1.identity, L1.history, L1.as-of, L1.current-version, L1.deletion-withdraws, L1.owner-standing, L1.statement-content, L1.omitted-facts-stand, L1.closed-account-activity, L1.unknown-codes, L1.constructed-scenarios
  - feedback: at most one current statement per customer and per account, and none once the latest statement is a withdrawal; statements of one thing do not overlap; any as-of question has exactly one answer with the standing facts of L1.statement-content; an account's as-of answer carries its customer's as-of answer
- **job:trade-lifecycle** — Know each trade's outcome and who owned it when it happened. Clauses: L1.identity, L1.as-of, L1.attribution-at-placement, L1.placement-moment, L1.lifecycle-mutates-outcome, L1.closed-account-activity, L1.deletion-withdraws, L1.unknown-codes, L1.constructed-scenarios
  - feedback: a later report of a trade changes its outcome fields and leaves its recorded ownership byte-identical; ownership equals the account's as-of statement at placement, not the current one; placement is the earliest held report's own time
- **job:positions** — Know what each account and customer holds, and how it got there. Clauses: L1.identity, L1.attribution-at-placement, L1.holdings-follow-trade, L1.no-phantom-positions, L1.deletion-withdraws, L1.unknown-codes, L1.constructed-scenarios
  - feedback: every holding change carries the ownership recorded on its causing trade; no statement of an account or customer sums below zero

## Clauses

### Identity and history

- **L1.identity** — Customers, accounts, and trades are the things the brokerage already identifies: a customer number, an account number, a trade number. A change to a customer or an account does not make it a different customer or account; it makes a new dated statement about the same one.
- **L1.history** — Every change to a customer or an account is kept, with the moment it took effect. Nothing about a customer or account is overwritten; a later statement sits beside the earlier one.
- **L1.as-of** — Any question about a customer or account can be asked as of a moment in time, and the answer is the statement in effect at that moment: the latest one that took effect at or before it.
- **L1.omitted-facts-stand** — A change that does not mention a standing fact leaves that fact as it last stood. A statement produced by such a change carries the fact at its last stated value. (Assumed under `issue-8-statement-content-assumed`; review trigger: the business confirms or amends.)
- **L1.closed-account-activity** — An account the brokerage recorded as closed keeps everything it already held, and closing it does not move or unwind any trade or holding already attributed to it. A trade placed on an account after that account's closing statement is recorded like any other and is reported for review, because either the closure or the trade is wrong and only the brokerage can say which. Activity never reopens an account: no trade creates a statement. (Accepted from `ce.l1.closed-account-activity` on 2026-09-17, closing `L1.hole.closed-account-activity`.)
- **L1.deletion-withdraws** — A report marking a record deleted withdraws the brokerage's assertion of that record from the moment that report states. It erases nothing. Every statement in effect before that moment stands exactly as it stood, and a question asked as of any earlier moment answers exactly as it did before the withdrawal was received. A withdrawal takes its place in the order of reports like any other report, and from its moment forward the record has no standing: a question asked as of that moment or later has no answer for that record, rather than an older one. A withdrawal creates nothing. It adds no customer, account, trade, or holding, and it neither opens nor closes an account. A withdrawal does not reach back through what already followed from the record: a holding or a position that followed a trade before that trade was withdrawn stands as history, because it records what the brokerage held at the time, and nothing is recomputed backwards. A thing whose only reports are withdrawals was never held at all: there is no earlier statement for a withdrawal to end, so no statement, no trade, and no holding comes into being from it, and it contributes to no position. Withdrawing a customer withdraws the standing of every account that customer owns, from that same moment, because an account's standing includes its owner's and there is no owner standing left to include; and because a customer that still owns accounts is one the brokerage may not have meant to withdraw, the withdrawal is reported for review. A trade or a holding is not asked as of a moment, so for these the clause reads: a withdrawn trade keeps its record and is marked withdrawn, it is not among the trades the brokerage asserts, and everything that already followed from it stands as history. (Accepted from `ce.l1.deletion-withdraws` on 2026-09-17, closing `L1.hole.deletions`; the owner-standing, reported-withdrawal and marked-withdrawn sentences accepted from `ce.l1.withdrawal-reaches-standing` on 2026-09-17.)
- **L1.current-version** — The current statement about a customer or account is the one with no later statement. There is at most one current statement per customer and per account: exactly one while the record stands, and none once its latest statement is a withdrawal under `L1.deletion-withdraws`.
- **L1.owner-standing** — An account's standing includes its owner's standing. When the brokerage says how an account stood at a moment, that includes how its customer stood at that same moment. It follows that an account has no standing at a moment when its owner has none: an account's as-of answer is never half an answer with the owner's part missing. (Second sentence accepted from `ce.l1.withdrawal-reaches-standing` on 2026-09-17, making explicit what `L1.deletion-withdraws` needed from this clause.)
- **L1.statement-content** — A dated statement carries the brokerage's standing facts at that moment. For a customer: whether the customer is active or inactive, and the customer's tier. For an account: whether the account is open or closed, its tax treatment, and which customer owns it. Names, addresses, contact details, and tax identifiers are not part of standing until a job needs them. (Assumed under `issue-8-statement-content-assumed`; review trigger: the business confirms or amends this enumeration.)

### Trades and ownership

- **L1.attribution-at-placement** — A trade belongs to the account, and through it the customer, as they stood at the moment the trade was placed. Later changes to that account or customer do not move a trade that was already placed, and do not move anything that trade created.
- **L1.placement-moment** — A trade is placed at the moment of the earliest report of it held by the brokerage, as that report states its own time. A trade whose earliest held report is not the trade's first lifecycle event is treated as placed at that report and marked as first seen late, so the ownership it fixes can be reviewed. An order sent straight to market has no pending stage of its own, so it is not first seen late when its earliest report is submitted; and where the brokerage's own systems record such an order as pending before routing it, that pending record is the order's own first lifecycle event, so it is not first seen late then either. (Placement assumed under `issue-8-statement-content-assumed`; the market-order sentence accepted from `ce.l1.first-seen-late-market-orders` on 2026-09-17; the pending-market-order sentence accepted from `ce.l1.market-order-seen-pending` on 2026-09-17, closing `L1.hole.market-order-seen-pending`.)
- **L1.lifecycle-mutates-outcome** — As a trade moves through its life (pending, submitted, completed, cancelled), its outcome changes: status, executed price, fees, commission, tax, quantity. Its ownership does not change. A later report of the same trade updates the outcome and leaves the ownership as first recorded.

### Holdings and positions

- **L1.holdings-follow-trade** — A change in what an account holds is caused by a trade. The holding change belongs to whoever owned the trade that caused it, as that trade's ownership was recorded. Holdings are never re-attributed by looking the account up again later.
- **L1.no-phantom-positions** — Summing holding changes for any one statement of an account or customer can never go below zero. A negative result means a holding was opened under one statement and closed under another, which the clauses above forbid.

### Evidence discipline

- **L1.unknown-codes** — The brokerage's records speak in a fixed vocabulary of codes (statuses, order types, change flags). A report carrying a code that vocabulary does not name is held for review and is not interpreted: no rule below may read a meaning into it, default it, or silently drop the report. Every job reports such a record as a violation, naming the record and the code. A report is held as a whole: one unknown code holds the record, not the field. A held report keeps its place in the order of reports, so the job can tell which report came first, but nothing else about it may be read. A held report changes nothing and creates nothing: every fact stands as it last stood, and a customer, account or trade known only through held reports is not yet known to the job; the hold itself is what is reported. (Second sentence is an authorized clarification, assumed under `issue-8-statement-content-assumed`; review trigger: business confirmation.)
- **L1.constructed-scenarios** — Any scenario built to test these rules, rather than received from the brokerage's records, is labeled as constructed wherever it appears and is never mixed into the received records. A constructed scenario changes something the received records already know; it never introduces a customer, account, or trade the brokerage does not have. One case is excepted, because it introduces nothing: a scenario may carry a withdrawal of a customer, account, or trade the records do not carry, since under `L1.deletion-withdraws` such a report asserts nothing and brings nothing into being, and a rule about what was never held cannot otherwise be exercised at all. The exception covers withdrawals only; a scenario may not name an identifier the records do not carry in any other kind of report. (Second sentence is an authorized clarification, assumed under `issue-8-statement-content-assumed`; review trigger: business confirmation. The withdrawal exception accepted from `ce.l1.withdrawal-reaches-standing` on 2026-09-17.)

## Holes

- **L1.hole.owner-change-reversions-account** — When a customer's standing changes, does the brokerage consider every account of that customer to have a new statement at that moment, or only the customer? The source data shows customer changes without matching account changes.
- **L1.hole.trade-timestamps** — Which moment counts as "when it completed" when a later report of a trade arrives without its full history? (Placement is settled, provisionally, by `L1.placement-moment`.)
- **L1.hole.change-effective-time** — Incremental change files carry no time of their own. Does a change in such a file take effect at the file's batch date, or at some other moment?
- **L1.hole.deletion-reversal** — May a withdrawal be undone? If a record is reported again after it was withdrawn, is that the same record resuming its standing, or is the later report something the brokerage must resolve first? `L1.deletion-withdraws` says a withdrawal ends a record's standing from its moment forward; it does not say whether anything can follow it. Until answered, no job may treat a report received after a withdrawal as resuming the record.
- **L1.hole.securities-and-brokers** — Securities, companies, and brokers are named in the records but not yet part of any job. When they are, the attribution rule must be restated for them.
- **L1.hole.held-first-report-placement** — When a trade's earliest report is held under `L1.unknown-codes` and a later report is not, is the trade placed at the earliest report the job can read, or is the trade itself held until the first report is resolved? The same question arises for every fact fixed at placement: if the earliest report that would supply the owning account or the order type is held while an earlier report of another kind is not, may a later report supply it? `L1.placement-moment` speaks of the earliest report the brokerage holds; a held report is one the brokerage has but may not read. Until answered, a trade any of whose placement-fixing facts would come from a held report is held.
- **L1.hole.batch-identity** — Does a report need to know which incremental file first delivered a fact?

## Anchors (fixed, not policy)

The received records are the TPC-DI 1.1.0 source files: CustomerMgmt actions for the historical load; Customer, Account, Trade, and HoldingHistory files for incremental loads; Trade and HoldingHistory for the historical load. Their field names and natural identifiers are structural facts listed in `chain/anchors/sources-v1.json`. They constrain shape only. They authorize no rule above.

## Simulation surface

A reviewer exercises a compiled chain by loading received records and any labeled constructed scenario, running the projection, and reading: the statements in effect for one customer and account over time; one trade's ownership and outcome before and after a later report; the holding changes and the position for each statement of an account and customer.

## Validation obligations

Deterministic: one current statement per customer and account; statements do not overlap; no persisted fact was derived from an unknown code; a trade's recorded ownership is unchanged by later reports; a holding change carries its trade's recorded ownership; no negative position per statement. Judgment: whether the compiled semantic model derives only what these clauses entail, leaves every hole open, and names the clause behind each element.
