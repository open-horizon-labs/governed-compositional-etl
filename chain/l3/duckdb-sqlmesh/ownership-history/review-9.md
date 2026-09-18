# Review 9 — `chain/l3/duckdb-sqlmesh/ownership-history/`

Reviewer: projection reviewer (capable model), adversarial re-review of the whole projection
against `chain/l2/ownership-history/selected-model.json` restricted to
`chain/l2/ownership-history/review.json`'s `selected_element_ids`.

Runs: `check` → `question`, zero problems, two questions. `run` → ok, 20/20 audits at zero.
`twophase` → ok, `changed_columns: []`. `compare duckdb-native --against duckdb-sqlmesh` →
`identical: true` on both tables. `simulate --ce ce-withdrawn-account-v1.json` → `ok`,
`silent: true`, no audit fired.

Every run is green. The projection nonetheless fails, on two defects that live entirely in the
unexercised withdrawal surface — which is where this review was told to look, and why `run`
showing zeros proves almost nothing.

---

## Q1 — the owner-cascade branch. Correct. This is the strongest part of the projection.

`models/account.sql` has the branch, and has it in the right form:

```sql
customer_withdrawn AS (
  SELECT DISTINCT customer_number
  FROM governed.customer
  WHERE is_withdrawal
)
...
    WHEN cw.customer_number IS NOT NULL THEN FALSE
...
LEFT JOIN customer_withdrawn AS cw
  ON cw.customer_number = f.owning_customer_number;
```

Checked against the three things the brief asked:

1. **Present.** Third branch of the `is_current` `CASE`, after own-withdrawal and
   reversal-foreclosure, before the latest-statement `ELSE`.
2. **Reads the sibling entity.** `FROM governed.customer`, not anything recomputed from
   `logical.account`'s own rows. `MODEL (... depends_on (governed.customer))` gives SQLMesh the
   edge, and `manifest.json`'s account artifact declares `governed.customer` in `reads` and
   `logical.customer.is_withdrawal` in `derived_from`. So the cross-entity read is declared in
   the two places the schema can hold it; only the handoff layer cannot express it.
3. **Keyed on existence, not on a date comparison.** The CTE is `WHERE is_withdrawal` with no
   correlation to `f.effective_from`; the join predicate is on `customer_number` alone. Nowhere
   in the branch does any customer `effective_from` appear. The failing form of reviews 15 and
   16 — `customer_withdrawal.effective_from <= f.effective_from` — is absent. I grepped the
   whole branch for it specifically, because that is the form that passes every audit on this
   fixture and is wrong for exactly the population `L1.owner-standing`'s second sentence is
   about.

Does the SQL match `logical.account.is_current`'s `parallel_assumption`? Yes, and it matches the
part that is easy to get wrong. The assumption's argument is that "current" asks about standing
at an unbounded, ever-advancing present, so what matters is whether a withdrawal exists at all,
not when it was dated relative to a statement that the withdrawal did not create; and it records
the exact condition under which the existence form stops being sound — a withdrawal dated later
than the present moment at which "current" is asked — together with why that is unreachable
today (`raw.customer_mgmt_action` is the only source carrying an `effective_from` and it names no
withdrawal action; the withdrawal-capable CDC sources carry no `effective_from` of their own and
stay deferred). The SQL's comment reproduces the first half of that argument in its own words
("an unbounded, ever-advancing present, not at the moment this statement was dated") and the
`DISTINCT` keeps the `LEFT JOIN` from fanning out account rows when a customer has several
withdrawal statements.

One gap, not a defect: the comment does **not** carry the future-dating revisit condition. The L2
review records that sentence as prescribed; a later Developer reading only `account.sql` sees the
existence form asserted but not the boundary at which it must be revisited, and existence-vs-date
is precisely the asymmetry that took three L2 rounds. Worth adding to the comment. It changes no
behavior, so it is not a finding.

`inv.account_single_current`'s audit uses the same existence form (`owner_withdrawn` CTE, no date
comparison), so the audit does not quietly re-introduce the date form behind a correct model.
Finding F2 below is about a different flaw in that same audit.

## F1 (blocking) — both `has_content` audits contradict the withdrawal exception their invariants now carry, and would fail the build on a correctly-projected withdrawal.

`audits/inv.account_statement_has_content.sql` is, in full body:

```sql
SELECT account_number, effective_from
FROM @this_model
WHERE status IS NULL OR tax_treatment IS NULL;
```

`inv.account_statement_has_content`'s selected statement is:

> Every candidate-sourced statement of an account **that is not itself a withdrawal
> (is_withdrawal = false)** carries a non-null status and a non-null tax_treatment ... **A
> withdrawal statement (is_withdrawal = true) carries neither status nor tax_treatment** ... and
> is not content-free under this invariant for that reason.

The audit has no `is_withdrawal = FALSE` guard. Its header comment has also dropped the exception
from its prose, stating the pre-move text verbatim.

The wrong behavior is concrete and is not a style point. `logical.account.status` and
`logical.account.tax_treatment` are both `nullable: true` in the selected model, each null
licensed specifically by `is_withdrawal = true`, and
`audits/inv.withdrawal_never_reaches_account_status.sql` **requires** the shape this audit
forbids:

```sql
WHERE is_withdrawal = TRUE
  AND (status IS NOT NULL OR tax_treatment IS NOT NULL);
```

So on the first withdrawal statement this job ever produces, two blocking audits over the same
model demand opposite things. `inv.withdrawal_never_reaches_account_status` fires if the
withdrawal carries facts; `inv.account_statement_has_content` fires if it does not. There is no
row a Developer can write that satisfies both. A correct projection of `L1.deletion-withdraws` —
a withdrawal asserts no standing, so `status` and `tax_treatment` are null — is a blocking build
failure under `inv.account_statement_has_content`, reported against the account and its
`effective_from` with no indication that the invariant excepts exactly that row. The two
tempting repairs are both wrong and are both named by the counterexample: null out nothing and
carry the last values forward (the CE's "must not restate the old one"), or write a
statement with empty facts (the CE's second `tempting_wrong_repair`, "leaves the record current
with empty facts"). The third option, adding `AND is_withdrawal = FALSE`, is the fix.

`audits/inv.customer_statement_has_content.sql` has the identical defect against
`inv.customer_statement_has_content`, whose statement carries the same exception for `status` and
`tier`, both of which are `nullable: true` in the selected model. The customer half is worse in
one respect: there is no `inv.withdrawal_never_reaches_customer_status` in the selected set, so
the customer withdrawal's null-fact shape is checked by nothing that should fire and by exactly
one audit that should not.

This is not an oversight the runs could have caught and it is not new work invented by this
review. `check` reports `sg.statement-content` among the five moved groups awaiting a stamp.
`sg.statement-content`'s members are exactly `inv.customer_statement_has_content`,
`inv.account_statement_has_content`, the four `matches_producing_source` invariants,
`inv.account_statement_never_created_by_activity`, `inv.withdrawal_never_reaches_account_status`,
and the four now-nullable content attributes. The projection answered that move for the one new
invariant (`inv.withdrawal_never_reaches_account_status`, present and correct) and for
`nullable: true` on nothing at all: `change-contract-7.md` scoped the cycle to
`inv.account_statement_never_created_by_activity` and explicitly said "every other audit
unchanged", and review 8 was scoped to the closed-account clause. The four content attributes
became nullable and the two `has_content` invariants gained their exception without any L3 cycle
carrying that into these two files. The moved group has not been answered, which is precisely
what the gate's first question puts to a reviewer. I do not stamp; I reject.

## F2 (blocking) — `inv.account_single_current`'s owner-cascade aggregate is per-account where the model's is per-statement, and fires on an account whose owner changed.

```sql
MAX(CASE WHEN w.customer_number IS NOT NULL THEN 1 ELSE 0 END) AS owner_withdrawn
...
GROUP BY a.account_number
...
OR ((own_withdrawn = 1 OR owner_withdrawn = 1) AND current_count <> 0);
```

The audit collapses the owner check to "does **any** statement of this account name a withdrawn
owner", then demands zero current statements for the whole account. The model's branch is
per-statement: `WHEN cw.customer_number IS NOT NULL THEN FALSE` is evaluated against
**that statement's own** `owning_customer_number`.

These differ whenever an account's owner changes across its statements, which
`raw.customer_mgmt_action` permits — `UPDACCT` carries its own `c_id`, and
`logical.account.owning_customer_number`'s `parallel_assumption` says only that the owner is
constant "unless a new account statement changes it", i.e. it may change. Concretely: account A
has a statement at t1 owned by customer C1 and a later statement at t2 owned by C2; C1 carries a
withdrawal, C2 does not.

- Model: t1 → `is_current = FALSE` (its own owner C1 is withdrawn). t2 → `is_current = TRUE`
  (latest statement, owner C2 stands). One current statement.
- `inv.account_single_current`'s own statement: "its **owning customer** still stands" — singular,
  the customer this account's standing statement names, which is C2. Exactly one is current.
  The model is right.
- Audit: `own_withdrawn = 0`, `owner_withdrawn = 1` (from t1), `current_count = 1` → returns
  account A. Blocking failure on correct data.

Same failure class as F1 and as the two the L2 reviews found: the audit's shape is not the
derivation's shape, and the fixture cannot tell, because it has no withdrawal and no
owner-changing account. The fix is to test the owner of the statement rather than to aggregate
over all of them — the `owner_withdrawn` flag belongs to the account's latest statement (or,
equivalently, the audit should count current statements and compare against the model's
per-statement condition), not to `MAX` over the account's history.

Note that the mirror audit `inv.account_asof_carries_customer_asof` gets this right: it joins
`customer_withdrawal_bound` on `a.owning_customer_number` per row, with no aggregation.

## F3 (non-blocking) — the carrying invariant is checked only at T values where its owner branch cannot fire.

`inv.account_asof_carries_customer_asof`'s L2 statement is over "any account_number and moment
T", and the L2 note designates it "the direct check of `inv.account_asof_has_unique_answer`'s own
owner branch ... keyed on T". The audit instantiates T only at each account statement's own
`effective_from`:

```sql
OR (w.first_withdrawal_from IS NOT NULL AND w.first_withdrawal_from <= a.effective_from)
```

For an owner-withdrawn account, every one of its own statements predates the owner's withdrawal —
that is the whole premise of the existence form — so `first_withdrawal_from <= a.effective_from`
is false at every T this audit tries. The branch it is designated to check is checked at exactly
the moments where it can never fire. Meanwhile
`audits/inv.account_asof_has_unique_answer.sql` reduces to a null-and-duplicate `effective_from`
check, so the owner branch of the as-of answer is projected nowhere: no column materializes it
and no audit samples a T at or after an owner withdrawal.

I am not calling this blocking. The as-of answer is not a materialized column here, consumers
derive it, and an audit cannot quantify over arbitrary T without generating candidate T values.
But the honest statement is that this projection carries no check of the as-of owner cascade, and
the available fix is cheap: union the customer withdrawal moments into the T set, so T ranges over
`{account statement effective_froms} ∪ {customer withdrawal effective_froms}`. Then the branch is
checked at the only T where it distinguishes anything. Worth doing in the cycle that fixes F1 and
F2.

## Q2 — nullability. The `owning_customer_number` asymmetry was **not** inherited; two other null paths exist.

`owning_customer_number` is `nullable: true` in the selected model, licensed only by
`is_withdrawal = true`, and its rule says so explicitly ("null for such a statement, licensed
only by `is_withdrawal = true`, exactly as status and tax_treatment are"). The projection is
consistent with the fixed L2, not the asymmetric one:
`audits/inv.account_owner_matches_producing_source.sql` carries the exception in both directions —
a non-withdrawal statement must equal the recomputed expected owner, and a
`is_withdrawal = TRUE` statement with a non-null owner is a violation (its second `UNION ALL`
arm). That is the symmetric treatment, and it is the audit that F1's two files should have
copied.

Null paths traced through both models:

- **`logical.account.status` from the constructed arm.** `CASE status_id WHEN 'ACTV' ... WHEN
  'INAC' ... END` yields null for any other `status_id`, on a row with `is_withdrawal = FALSE` —
  a null not licensed by the model. `ce.account_changes.status_id` is unconstrained in the anchor
  and `inv.unknown_codes_held` deliberately does not check that source. Not a finding, because
  review 3's fix landed: `inv.account_status_matches_producing_source` now compares against
  `c.status_id` unwrapped, so the row fails blocking with the right invariant's name rather than
  surfacing as a mis-named content violation. It fails loudly. I note it only because F1 removes
  the second net under it.
- **`logical.customer.customer_number` (nullable: false) is unguarded.** A
  `raw.customer_mgmt_action` row with `action_type` in (NEW, UPDCUST, INACT) and a null `c_id`
  produces a customer statement with a null `customer_number`. Trace every customer audit:
  `inv.customer_status_matches_producing_source` and `inv.customer_tier_matches_producing_source`
  both use inner `JOIN ... ON a.c_id = m.customer_number`, and `NULL = NULL` is not true, so the
  row is silently dropped from both rather than reported; `inv.customer_single_current` groups by
  `customer_number`, DuckDB partitions nulls together, the single row is current, `count = 1`,
  pass; `inv.customer_statements_no_overlap` and `inv.customer_asof_has_unique_answer` test
  `effective_from`, which is populated. So a statement violating a `nullable: false` identifier
  passes all six customer audits. The account side does not have this hole: a null
  `account_number` is caught, because `inv.account_statement_never_created_by_activity` uses
  `LEFT JOIN` and reports the row when no producer matches. Low severity, off the withdrawal
  path, and arguably pre-existing rather than moved — but it is an unguarded null on a
  non-nullable column and should be closed in the same cycle.
- Everything else is guarded. `tax_treatment` null on a first-statement `CLOSEACCT` and `tier`
  null on a first-statement `INACT` are caught blocking by the `has_content` audits;
  `owning_customer_number` null on a constructed first statement is caught by
  `inv.constructed_account_change_refers_to_known_account` and independently by
  `inv.account_asof_carries_customer_asof`'s `a.owning_customer_number IS NULL` arm; a null
  `effective_from` is caught by both `asof_has_unique_answer` audits.

## Q3 — zero current statements. The models permit it; `single_current` does not treat it as a violation; F1 does, indirectly.

Both `is_current` expressions can evaluate `FALSE` for every statement of a key — nothing forces a
row true, because the `MAX(...) OVER` comparison sits in the `ELSE` arm after the three `FALSE`
branches. Both `single_current` audits are two-sided and require zero, not one, once a withdrawal
exists:

- `inv.customer_single_current`: `withdrawals = 0 AND currents <> 1` OR `withdrawals > 0 AND
  currents <> 0`.
- `inv.account_single_current`: `own_withdrawn = 0 AND owner_withdrawn = 0 AND current_count <> 1`
  OR `(own_withdrawn = 1 OR owner_withdrawn = 1) AND current_count <> 0`.

Neither treats zero as a violation in the withdrawn case, and neither treats one as acceptable
there. `type.statement_is_current` no longer says "exactly one", matching
`L1.current-version`'s weakening. No other audit reads `is_current` at all — I checked all
twenty. Correct, subject to F2's separate flaw in how `owner_withdrawn` is computed.

The indirect defect: under F1, a withdrawn record cannot reach the state where zero-current is
evaluated, because the build fails on the withdrawal statement's null facts first. So the
zero-current path is correct and unreachable.

## Q4 — `blocking false`. Exactly one, on the right audit. Enumerated in both directions.

Grepped `blocking` across all twenty audit files. One occurrence:

```
audits/inv.customer_withdrawal_with_standing_accounts_reported.sql:1:
  AUDIT (name "inv.customer_withdrawal_with_standing_accounts_reported", blocking false);
```

Every other audit header is a bare `AUDIT (name "...")` with no second argument, so each defaults
to blocking. The nineteen: `constructed_account_change_refers_to_known_account`,
`account_statements_no_overlap`, `account_tax_treatment_matches_producing_source`,
`account_asof_has_unique_answer`, `customer_tier_matches_producing_source`,
`customer_statement_has_content`, `withdrawal_never_reaches_account_status`,
`constructed_scenarios_labeled`, `customer_statements_no_overlap`,
`account_statement_never_created_by_activity`, `account_statement_has_content`,
`account_asof_carries_customer_asof`, `customer_single_current`,
`account_owner_matches_producing_source`, `customer_asof_has_unique_answer`,
`customer_status_matches_producing_source`, `account_status_matches_producing_source`,
`unknown_codes_held`, `account_single_current`.

Other direction: the selected model has `reports: true` on exactly one invariant,
`inv.customer_withdrawal_with_standing_accounts_reported`, and on no other — I enumerated
`reports` across all twenty selected invariants and the other nineteen carry no such key. The two
sets are the same singleton. No must-hold audit is quietly non-blocking, and the one reporting
audit is not quietly must-hold.

The reporting audit's body is also right about the thing that makes a non-blocking audit
dangerous — abstention. It does not merely look for withdrawn customers with standing accounts;
its second and third `UNION ALL` arms report an account as *unevaluable* when
`owning_customer_number` is null or when the named customer has no row in `governed.customer` at
all, rather than passing over it as though the condition were false. That is the L2 statement's
second sentence, implemented. Its zero rows on the fixture are an honest empty result of an
unexercised condition, and the header comment says so rather than claiming a pass.

## Q5 — headers and write surface. Correct.

Both models are `kind FULL, dialect duckdb`. Both entities are `history: versioned` in the
selected model, and `chain/profiles/duckdb-sqlmesh.json` gives
`strategy_for_versioned: "FULL rebuild from the complete change feed"`. `manifest.json` states
the same strategy for both artifacts, with the reads each model actually performs. `FULL` is the
profile's answer for versioned, so no `governed_merge` custom materialization is used here and
none should be — the profile reserves that for `incremental_by_identity`, which neither entity
is, and its `native_merge: false` caveat is therefore not engaged.

Write surface: no attribute of either entity carries `frozen` or `per_statement` in the selected
model, so there is no protected column to update in place; and a `FULL` rebuild has no
`WHEN MATCHED` arm at all, so no write path can update anything. `check`'s write-surface guard
returns zero problems and `twophase` reports `changed_columns: []` with account 428's three
statements unchanged across the rollover. Consistent.

## Q6 — the permitted undeclared dependency. Permitting it was right, and this is the legitimate case.

`check`'s second question: `models/account.sql` reads `governed.customer`, which no handoff
declares.

Permitting it was right. The alternatives are all worse and two of them are known defects. Refuse
it and the Developer must either drop the owner-cascade branch — the defect L2 reviews 15 and 16
found, twice — or invent a handoff from `logical.customer.is_withdrawal` into
`logical.account.is_current`, which would be a fabricated element not in
`selected_element_ids` and would misdescribe the relation, since a handoff maps a *source field*
to an attribute and `logical.customer` is not a source. The real situation is that a derivation
spans two entities of one job and `semantic-model-v2.schema.json` has no
`derivation.kind` for that, which is a schema limitation, recorded as such in the L2 review's
notes and in the L2-to-L3 contract. A gate that refuses the only correct SQL because the schema
cannot name the relation is the gate being wrong, and the Developer's argument was sound.

This use is the legitimate case, on four counts. It is intra-job — `governed.customer` is a
sibling artifact of this same manifest, not another job's output, so no cross-job containment is
bypassed. It is one-directional: `customer.sql` reads only `raw.customer_mgmt_action` and never
`governed.account`, so there is no cycle, and `depends_on (governed.customer)` in the account
header gives SQLMesh the ordering explicitly rather than leaving it to inference. It reads
exactly one selected fact, `logical.customer.is_withdrawal`, which is declared in the account
artifact's `derived_from`, and it reads it as `WHERE is_withdrawal` and nothing else — no status,
no tier, no smuggled second rule. And it introduces no new source: `governed.customer` is derived
wholly from a source this job already declares.

One correction to the gate's wording: it says "the dependency is stated only in the derivation's
rule text". That is not so here. It is stated in the L2 attribute's rule text, in the L2
invariant's statement, in the manifest's `reads`, in the manifest's `derived_from`, in the
model's `depends_on`, and in a comment block in the SQL naming it as the cross-entity read. The
projection is as honest about this dependency as the schema permits. The gate's message should
be softened to say the *handoff layer* cannot express it, not that the dependency is
undocumented, or a future reviewer will read the question as a defect it is not.

Both of `check`'s questions are indeed not problems in themselves. But the first one is not
merely bookkeeping: answering the `sg.statement-content` move is what F1 shows was never done,
so the stale fingerprints are stale for a reason.

## Q7 — `compare` is identical, and the agreement is coincidence on everything this review is about.

`compare duckdb-native ownership-history --against duckdb-sqlmesh` reports
`identical: true`, `columns_match: true`, 2/2 customer rows and 5/5 account rows. That is real
evidence, and it covers a real surface: the `action_type` → status mapping, the two
`LAST_VALUE(... IGNORE NULLS)` carry-forwards, the constructed-scenario union and its provenance
labelling, the latest-statement `ELSE` arm of `is_current`, and the `(key, effective_from)`
grain.

It is coincidence on the withdrawal surface, and the mechanism is not subtle. The fixture
contains no row with `is_withdrawal = true`, and none can: `from_actions` and `from_constructed`
in `account.sql` and `base` in `customer.sql` each hardcode `FALSE AS is_withdrawal`, because
`raw.customer_mgmt_action`'s vocabulary names no withdrawal action and `ce.account_changes` has no
field that could signal one. Therefore `account_withdrawal_bound`, `withdrawal_bound` and
`customer_withdrawn` are all empty relations, all three `FALSE` branches of the account
`is_current` `CASE` and both of the customer one are dead, and `compare` is comparing two
engines' evaluation of the `ELSE` arm. Two projections that disagreed completely about what a
withdrawal means — one using the existence form, one the date-comparison form that failed twice —
would compare identical on this fixture. `compare` also takes no `--ce`, so the one fixture that
carries a `D` row cannot even be fed to it. This is the same reason `simulate` returns
`silent: true`: the CE's `raw_additions.account_cdc` `D` row for account 624 is never read,
because all seven CDC handoffs remain deferred under `L1.hole.change-effective-time`, so 624
keeps its 2010-02-07 statement current and an as-of question at 2018 still answers with a
statement the brokerage has withdrawn. The harness reports that as silence, not failure, which is
right — the CE is `proposed` and its own `blocked_on` names this hole for both halves.

What would make the two engines diverge, concretely, in order of what I would try first:

1. **Undefer one `cdc_flag` → `is_withdrawal` handoff** (`handoff.raw.account_cdc.cdc_flag->logical.account.is_withdrawal`
   or its customer twin). This is the precondition for everything below; until
   `L1.hole.change-effective-time` is answered, nothing in this job can produce a true
   `is_withdrawal` and no fixture can separate the two targets.
2. **Then the existence-vs-date fork appears.** A target using
   `withdrawal.effective_from <= account.effective_from` for the owner cascade, against one using
   set membership, diverge on exactly the population the CE builds: an account whose own last
   statement long predates its owner's withdrawal. The date form reports `is_current = true`; the
   existence form reports `false`. Both pass every audit on today's fixture. This is the
   divergence the projection is built to avoid and the one `compare` currently cannot see.
3. **`INNER` instead of `LEFT JOIN` on `customer_withdrawn`** would silently drop every account
   whose owner is not withdrawn — a row-count divergence, visible immediately, and the reason the
   `LEFT JOIN` here is load-bearing rather than stylistic.
4. **Dropping the `DISTINCT`** from `customer_withdrawn` would fan out account rows once per
   withdrawal statement of the owner, diverging on row count against a target that kept it.
5. **The `<=` vs `<` boundary** in the reversal-foreclosure branches, at a statement dated exactly
   at the withdrawal's own moment.
6. **F1 and F2 themselves.** If the native target guarded its `has_content` audits on
   `is_withdrawal`, or keyed `single_current`'s owner flag per statement, then the moment a
   withdrawal exists one target's build fails and the other's does not — a divergence in
   `both_ok` rather than in rows, which is the failure `compare`'s current green result gives no
   warning of.

Until step 1, `compare`'s `identical: true` should be read as "the two targets agree about
accounts and customers that have never been withdrawn", which is all this fixture contains.

---

## What would have changed my mind

I went looking for reasons F1 is not a defect and did not find them.

- If `logical.account.status`, `logical.account.tax_treatment`, `logical.customer.status` and
  `logical.customer.tier` were `nullable: false`, the unguarded `has_content` audits would be
  correct. All four are `nullable: true` in the selected model.
- If some other selected invariant asserted that a withdrawal statement carries non-null facts,
  the contradiction would be in the L2 and not mine to reject. I read all twenty selected
  invariant statements; none does, and
  `inv.withdrawal_never_reaches_account_status` asserts the opposite.
- If the two `has_content` invariants were outside `selected_element_ids`, or in a group not
  reported as moved, the projection would be entitled to the pre-move text. Both are selected and
  both are members of `sg.statement-content`, which `check` reports as moved.
- If a withdrawal statement could never be produced even after the hole is answered, F1 would be
  theoretical. `logical.account.is_withdrawal`'s own rule names the handoff that will set it
  (`raw.account_cdc.cdc_flag = 'D'`), and the accepted `ce.l1.deletion-withdraws` plus the
  proposed CE both describe the row that will trigger it.

For F2, I would have withdrawn it if the selected model asserted that
`owning_customer_number` is constant across an account's statements. It does not — its
`parallel_assumption` says constant "unless a new account statement changes it", and
`UPDACCT` carries its own `c_id`, so the divergent case is reachable from a received source with
no CDC and no withdrawal-capable handoff required. Only a withdrawn customer is needed, which
puts F2 behind the same hole as F1 but not behind anything more.

The answer to the question this review was most wanted to test is that the branch is right — and
it is right in the specific way that took the L2 three rounds to reach, keyed on existence, in
the sibling entity, with the reasoning written down beside it. If F1 and F2 were the only things
standing between this projection and acceptance, that is because the parts that were hard were
done carefully and the parts that were assumed unchanged were not re-read against a model that
had moved underneath them. `sg.statement-content` moved; two of its audits did not.

Defects, not fixes: F1 and F2 are blocking, F3 and the `customer_number` null path in Q2 should
be closed in the same cycle, and the future-dating sentence belongs in `account.sql`'s comment. I
have written no `.sql`, no `manifest.json`, no `review.json`, and I have not stamped.

VERDICT: fail
