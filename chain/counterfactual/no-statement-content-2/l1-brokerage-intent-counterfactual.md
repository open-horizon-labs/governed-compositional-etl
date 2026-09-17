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

- **job:ownership-history** — Know how any customer or account stood at any moment, and who owned what. Clauses: L1.identity, L1.history, L1.as-of, L1.current-version, L1.owner-standing, L1.constructed-scenarios
  - feedback: one current statement per customer and per account; statements of one thing do not overlap; any as-of question has exactly one answer; an account's as-of answer carries its customer's as-of answer
- **job:trade-lifecycle** — Know each trade's outcome and who owned it when it happened. Clauses: L1.identity, L1.as-of, L1.attribution-at-placement, L1.placement-moment, L1.lifecycle-mutates-outcome, L1.constructed-scenarios
  - feedback: a later report of a trade changes its outcome fields and leaves its recorded ownership byte-identical; ownership equals the account's as-of statement at placement, not the current one; placement is the earliest held report's own time
- **job:positions** — Know what each account and customer holds, and how it got there. Clauses: L1.identity, L1.attribution-at-placement, L1.holdings-follow-trade, L1.no-phantom-positions, L1.constructed-scenarios
  - feedback: every holding change carries the ownership recorded on its causing trade; no statement of an account or customer sums below zero

## Clauses

### Identity and history

- **L1.identity** — Customers, accounts, and trades are the things the brokerage already identifies: a customer number, an account number, a trade number. A change to a customer or an account does not make it a different customer or account; it makes a new dated statement about the same one.
- **L1.history** — Every change to a customer or an account is kept, with the moment it took effect. Nothing about a customer or account is overwritten; a later statement sits beside the earlier one.
- **L1.as-of** — Any question about a customer or account can be asked as of a moment in time, and the answer is the statement in effect at that moment: the latest one that took effect at or before it.
- **L1.current-version** — The current statement about a customer or account is the one with no later statement. There is exactly one current statement per customer and per account.
- **L1.owner-standing** — An account's standing includes its owner's standing. When the brokerage says how an account stood at a moment, that includes how its customer stood at that same moment.

### Trades and ownership

- **L1.attribution-at-placement** — A trade belongs to the account, and through it the customer, as they stood at the moment the trade was placed. Later changes to that account or customer do not move a trade that was already placed, and do not move anything that trade created.
- **L1.placement-moment** — A trade is placed at the moment of the earliest report of it the brokerage holds, as that report states its own time. A later report of a trade the brokerage has not seen before is treated as its placement and marked as first seen late, so the ownership it fixes can be reviewed.
- **L1.lifecycle-mutates-outcome** — As a trade moves through its life (pending, submitted, completed, cancelled), its outcome changes: status, executed price, fees, commission, tax, quantity. Its ownership does not change. A later report of the same trade updates the outcome and leaves the ownership as first recorded.

### Holdings and positions

- **L1.holdings-follow-trade** — A change in what an account holds is caused by a trade. The holding change belongs to whoever owned the trade that caused it, as that trade's ownership was recorded. Holdings are never re-attributed by looking the account up again later.
- **L1.no-phantom-positions** — Summing holding changes for any one statement of an account or customer can never go below zero. A negative result means a holding was opened under one statement and closed under another, which the clauses above forbid.

### Evidence discipline

- **L1.constructed-scenarios** — Any scenario built to test these rules, rather than received from the brokerage's records, is labeled as constructed wherever it appears and is never mixed into the received records. A constructed scenario changes something the received records already know; it never introduces a customer, account, or trade the brokerage does not have. (Second sentence is an authorized clarification, assumed under `issue-8-statement-content-assumed`; review trigger: business confirmation.)

## Holes

- **L1.hole.owner-change-reversions-account** — When a customer's standing changes, does the brokerage consider every account of that customer to have a new statement at that moment, or only the customer? The source data shows customer changes without matching account changes.
- **L1.hole.closed-account-activity** — Trades appear on accounts the brokerage recorded as closed years earlier (account 428 closed in 2012, trades in 2017). Is that a data error, a reopening the records omit, or does a closed account still own trades?
- **L1.hole.trade-timestamps** — Which moment counts as "when it completed" when a later report of a trade arrives without its full history? (Placement is settled, provisionally, by `L1.placement-moment`.)
- **L1.hole.change-effective-time** — Incremental change files carry no time of their own. Does a change in such a file take effect at the file's batch date, or at some other moment?
- **L1.hole.deletions** — Incremental files can mark a record deleted. What does deleting a trade or account mean for history, ownership, and holdings?
- **L1.hole.securities-and-brokers** — Securities, companies, and brokers are named in the records but not yet part of any job. When they are, the attribution rule must be restated for them.
- **L1.hole.batch-identity** — Does a report need to know which incremental file first delivered a fact?

## Anchors (fixed, not policy)

The received records are the TPC-DI 1.1.0 source files: CustomerMgmt actions for the historical load; Customer, Account, Trade, and HoldingHistory files for incremental loads; Trade and HoldingHistory for the historical load. Their field names and natural identifiers are structural facts listed in `chain/anchors/sources-v1.json`. They constrain shape only. They authorize no rule above.

## Simulation surface

A reviewer exercises a compiled chain by loading received records and any labeled constructed scenario, running the projection, and reading: the statements in effect for one customer and account over time; one trade's ownership and outcome before and after a later report; the holding changes and the position for each statement of an account and customer.

## Validation obligations

Deterministic: one current statement per customer and account; statements do not overlap; a trade's recorded ownership is unchanged by later reports; a holding change carries its trade's recorded ownership; no negative position per statement. Judgment: whether the compiled semantic model derives only what these clauses entail, leaves every hole open, and names the clause behind each element.
