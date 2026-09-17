# Incremental DimTrade: mutation roles, the MERGE guard, and the SQLMesh workaround

Phase 2 extends the bounded historical slice with one incremental change: a trade completes after its account has acquired a new SCD2 version. The tempting write rebinds the trade's account and customer surrogate keys to the current account version. Every foreign key stays valid, the grain holds, and historical ownership silently changes. FactHoldings inherits the wrong attribution.

The governing Sketch is [`sketches/trade-dim-incremental-v1.md`](../sketches/trade-dim-incremental-v1.md). It extends `trade-dim-v1` and keeps its holes.

## Where the policy lives

Policy lives in one place: the `mutation_role` on each semantic type in [`contracts/incremental/semantic-types/dim-trade-incremental-types-v1.json`](../contracts/incremental/semantic-types/dim-trade-incremental-types-v1.json) (schema `semantic-types/v2`, under `contracts/incremental/schema/`).

| Role | Meaning | Types in this slice |
|---|---|---|
| `identity` | matches an existing row | `trade_id` |
| `frozen_from_first_encounter` | written on insert only, never on match | `account_surrogate_key`, `customer_surrogate_key` |
| `mutable` | written on insert and on match | `status_id`, `share_quantity`, `usd_per_share`, `usd_amount` |
| `none` | never projected into the dimension | `cdc_flag`, `cdc_sequence`, `account_natural_id` |

Columns inherit roles through their semantic type in the logical model. A contract that puts a role on a column name is rejected. The edge contract restates no column list; the compiler rejects one if it appears.

## What the compiler does

`scripts/compile_incremental.py compile`:

1. Validates the Sketch text, the v2 type registry, the logical model, the stage contract, the edge contract (schema `edge-contract/v2`, which admits `assumed` rules under an approved decision), and the repair authority.
2. Derives column roles and the update surface. It refuses to proceed if the frozen role is used on fewer than two columns, because a single-use role is per-case policy.
3. Builds a SQLGlot `Merge` whose `WHEN MATCHED THEN UPDATE SET` contains exactly the mutable-role columns, and runs the guard on its own output.
4. Renders a SQLMesh project: a FULL stage model, a `kind CUSTOM` target model and an insert-only key-binding model both using the `governed_merge` materialization, and two audits.

The rendered MERGE is written to `generated/dim_trade_incremental.merge.sql` for review. It is projection, not policy.

## The guard

`scripts/merge_guard.py` inspects any SQL that could write the target, whoever wrote it. It reports each attempted write to a frozen-role column with the path it took:

- `WHEN MATCHED THEN UPDATE SET` naming a frozen column, directly, alias-qualified, or through an expression;
- `WHEN MATCHED THEN DELETE` paired with `WHEN NOT MATCHED THEN INSERT`, which rebinds by deleting and reinserting;
- a plain `UPDATE` of a frozen column, a `DELETE` from the target followed by reinsert, or `INSERT ... ON CONFLICT DO UPDATE` touching a frozen column.

```bash
.venv/bin/python scripts/compile_incremental.py guard candidate.sql
```

On the naive MERGE the output is:

```text
Trade CDC stage                 PASS
DimTrade row/FK checks          PASS
Incremental lifecycle contract  FAIL
  attempted write:
    sk_account_id  (via when_matched_update_set)
    sk_customer_id  (via when_matched_update_set)
  semantic role:
    frozen_from_first_encounter
Holdings attribution path       AFFECTED
    logical.fact_holdings
    metric.position_by_account
    metric.position_by_customer
```

The conventional repair, a MERGE whose update list omits the key columns, passes the guard. That repair is legitimate and complete for this incident. What it does not carry is the rule: the next frozen column or the next consumer gets no protection until someone writes another regression.

## The workaround, named in the Sketch

SQLMesh 0.236.x has no native `MERGE` on DuckDB. Its `INCREMENTAL_BY_UNIQUE_KEY` kind materializes as delete-by-key plus insert of whole rows and raises on a matched-update clause. There is nothing for the guard to constrain. DuckDB 1.4+ executes `MERGE INTO` natively, and SQLGlot emits it.

The `governed_merge` materialization (`materializations/governed_merge.py` in the rendered project) executes the compiler-built `Merge` through the SQLMesh engine adapter. The Sketch names it under "Projection workaround (not policy)" with a retirement trigger. It receives the mutable and frozen column lists as materialization properties, re-checks them, and refuses to run if they overlap. The repair authority forbids editing it.

## Verify twice

- **Guard, before plan.** Mechanical inspection of the AST. Proves the compiler's intent and rejects hand-written rebinds.
- **Gate, after run.** The audit `frozen_keys_bound_once` joins the dimension to the append-only key-binding model and fails on any frozen column that differs. Proves the engine's behavior. A write that bypasses both SQLMesh and the guard still fails here.

## The counterexample

[`counterexamples/archive/ce-account-428-rollover-v1.json`](../counterexamples/archive/ce-account-428-rollover-v1.json) is constructed. DIGen Batch2 and Batch3 contain no Account CDC row for account 428, so the rollover between trade 372101's `SBMT` and `CMPT` rows is injected and labeled. The trade rows are real Batch2 records. The CE was accepted because its general rule names semantic roles, not identifiers. It lives in a phase-2 archive index and regression set; the phase-1 index and set are unchanged.

```bash
.venv/bin/python scripts/compile_incremental.py ce
```

builds a disposable DuckDB from the fixture, runs the projection at first encounter, swaps in the Batch2 CDC rows and the rolled-over account, restates, and reports the before and after rows plus the audit result.

## Authority status

The rules are `assumed` under [`.oh/metis/issue-8-incremental-key-binding-adjudication.md`](../.oh/metis/issue-8-incremental-key-binding-adjudication.md). The TPC-DI 1.1.0 clause for incremental DimTrade has not been read here, so no clause number is recorded. The hole `incremental.authority-locator` stays open and the compiler refuses to run if it is closed without a specification read.
