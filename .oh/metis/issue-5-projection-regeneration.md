---
id: issue-5-projection-regeneration
title: "Treat SQLMesh execution as a disposable matched projection"
outcome: governed-compositional-etl-repair
---

# Projection regeneration decision

**Date:** 2026-08-13

**Decision hat:** experiment lead

**Issue:** #5

## Decision

Compile one canonical SQLMesh project from the current Sketch, structural anchors, and contracts, then copy those exact bytes into the native, stage-local CESS, and compositional CESS starting directories. Generated SQLMesh models, SQLGlot expressions, SQL, audits, SQLMesh state, and DuckDB tables remain projections or execution evidence rather than policy authority.

The compiler input allowlist excludes the oracle, CE archive, repair submissions, and private custody paths. A fresh test deletes the ignored generated project and requires the rebuilt manifest and arm bytes to match.

## Evidence and boundary

SQLMesh loads all six generated models, executes them on persistent DuckDB, and passes six audit applications. The retained manifest maps governing clauses and rule IDs to models, SQLGlot expressions, and audits. A separate domain-reviewer-hat Sketch review passes the bounded materialized example without resolving any open hole.

This retires projection-regeneration risk for the selected historical slice. It establishes equivalent starting projection bytes, data connection, and dependency versions across the three arms. It does not establish equal failure reveal order, repair budget, or reviewer access; issue #7 must enforce those run conditions. If those conditions diverge, the issue #5 equivalence claim is insufficient and the experiment review trigger fires.
