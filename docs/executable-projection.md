# Replaceable SQLMesh projection

Issue #5 compiles the bounded historical trade Sketch, structural anchors, and semantic contracts into an executable SQLMesh DAG on persistent DuckDB. The generated project lives under ignored `build/issue5-projection/`; deleting it loses no governing policy.

## Inputs and exclusions

The compiler has an explicit input allowlist in `scripts/compile_projection.py`. It reads:

- the human-reviewed Trade Sketch;
- issue #3 structural source anchors;
- source, logical-model, semantic-type, stage, edge, repair-authority, and artifact-classification contracts.

It does not read the oracle corpus, public or held-out oracle fixtures, repair submissions, the accepted-counterexample archive, or private custody paths. Policy-bearing creation and close expressions come from the current edge contract and are constructed as SQLGlot ASTs before DuckDB SQL is rendered.

## Generated projection

The disposable SQLMesh project contains six models:

1. local Trade and TradeHistory stages;
2. TradeType and StatusType reference stages;
3. the governed lifecycle edge projection;
4. the logical DimTrade projection.

SQLMesh executes this DAG against `build/tpcdi.duckdb`, the persistent issue #2 substrate. The retained `projection/manifest-v1.json` maps source clauses and rule IDs to models, SQLGlot expressions, and audits. It also pins the compiler input hashes and executable dependency versions.

## Two separate acceptance checks

The compiler emits deterministic SQLMesh audits for encodable invariants: non-null trade identity and valid lifecycle ordering. Passing these audits is not semantic acceptance. A capable reviewer must separately compare the simulated result with `sketches/trade-dim-v1.md`. The manifest records both obligations and never labels an audit as Sketch review.

## Rebuild and execute

Install the pinned development dependencies, reuse the verified issue #2 substrate, and run:

```sh
python3 -m pip install -r requirements-dev.txt
mise exec -- python3 scripts/tpcdi.py smoke --reuse
python3 scripts/compile_projection.py fresh
python3 scripts/compile_projection.py execute
```

`fresh` deletes only the known ignored projection directory, recompiles from the allowlisted governing inputs, and requires byte/logical equivalence. `execute` applies the SQLMesh project, runs its audits, and retains bounded execution evidence under `evidence/issue-5/`.

## Matched starting point

The compiler copies one canonical generated project into `native`, `stage_local_cess`, and `compositional_cess` arm directories, then verifies every file byte against the same manifest. This establishes equivalent starting models, expressions, audits, data connection, and dependency versions. It does not yet establish matched reveal order, repair budget, or reviewer context; those remain experiment-run obligations for issue #7.

This is a research projection, not a compliant TPC-DI benchmark or a comparative performance result. Canonical tool-package and publication-policy review remain human gates.
