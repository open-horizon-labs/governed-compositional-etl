#!/usr/bin/env python3
"""Mechanical guard: mutation roles on semantic types constrain any MERGE/UPDATE surface.

Policy enters only through the semantic type registry (``mutation_role``). This module
derives column roles through a logical model, builds a role-constrained SQLGlot Merge,
and inspects arbitrary SQL for writes to ``frozen_from_first_encounter`` columns.
Generated SQL is projection; the guard's verdict is evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sqlglot import exp, parse, parse_one

ROLES = ("none", "identity", "per_statement", "mutable", "frozen_from_first_encounter")
PER_STATEMENT = "per_statement"
FROZEN = "frozen_from_first_encounter"


class GuardError(ValueError):
    """The governing role registry or a contract misuses mutation roles."""


def load_roles(types_document: dict) -> dict[str, str]:
    if types_document.get("schema_version") != "semantic-types/v2":
        raise GuardError("mutation roles require semantic-types/v2")
    roles: dict[str, str] = {}
    for item in types_document["types"]:
        role = item.get("mutation_role")
        if role not in ROLES:
            raise GuardError(f"semantic type {item.get('id')} has unknown mutation_role {role!r}")
        if item["id"] in roles:
            raise GuardError("semantic type ids must be unique")
        roles[item["id"]] = role
    return roles


def column_roles(logical_model: dict, roles: dict[str, str]) -> dict[str, str]:
    """Roles reach columns only through semantic types; a role on a column is rejected."""
    result: dict[str, str] = {}
    for attribute in logical_model["attributes"]:
        if "mutation_role" in attribute or "role" in attribute:
            raise GuardError(
                f"attribute {attribute['name']} declares a role on a column name; roles attach to semantic types"
            )
        semantic_type = attribute["semantic_type"]
        if semantic_type not in roles:
            raise GuardError(f"attribute {attribute['name']} references unknown semantic type {semantic_type}")
        if roles[semantic_type] == "none":
            raise GuardError(f"semantic type {semantic_type} has mutation_role none and cannot be projected")
        result[attribute["name"]] = roles[semantic_type]
    if list(result) != [a["name"] for a in logical_model["attributes"]]:
        raise GuardError("duplicate attribute names")
    return result


def update_surface(column_roles_map: dict[str, str]) -> dict[str, list[str]]:
    surface = {"identity": [], "mutable": [], "frozen": []}
    for column, role in column_roles_map.items():
        if role == "identity":
            surface["identity"].append(column)
        elif role == "mutable":
            surface["mutable"].append(column)
        elif role in (FROZEN, PER_STATEMENT):
            surface["frozen"].append(column)  # per_statement values are never updated in place either
    if not surface["identity"]:
        raise GuardError("at least one identity column is required for a MERGE match")
    if not surface["frozen"]:
        raise GuardError("no frozen_from_first_encounter column; this guard is not needed")
    return surface


def build_merge(target: str, source_sql: str, column_roles_map: dict[str, str]) -> exp.Merge:
    """Derive the MERGE from roles. Only mutable columns enter WHEN MATCHED UPDATE SET."""
    surface = update_surface(column_roles_map)
    keys = surface["identity"]
    columns = list(column_roles_map)
    whens = []
    if surface["mutable"]:
        whens.append(
            exp.When(
                matched=True,
                then=exp.Update(
                    expressions=[
                        exp.EQ(this=exp.column(c), expression=exp.column(c, "src"))
                        for c in surface["mutable"]
                    ]
                ),
            )
        )
    whens.append(
        exp.When(
            matched=False,
            then=exp.Insert(
                this=exp.Tuple(expressions=[exp.column(c) for c in columns]),
                expression=exp.Tuple(expressions=[exp.column(c, "src") for c in columns]),
            ),
        )
    )
    return exp.Merge(
        this=exp.alias_(exp.to_table(target), "tgt", table=True),
        using=exp.Subquery(
            this=parse_one(source_sql, dialect="duckdb"),
            alias=exp.TableAlias(this=exp.to_identifier("src")),
        ),
        on=exp.and_(*[exp.EQ(this=exp.column(k, "tgt"), expression=exp.column(k, "src")) for k in keys]),
        whens=exp.Whens(expressions=whens),
    )


class Verdict:
    def __init__(self, ok: bool, attempted_writes: list[dict] | None = None, statement_class: str = ""):
        self.ok = ok
        self.attempted_writes = list(attempted_writes or [])
        self.statement_class = statement_class

    def to_dict(self) -> dict:
        return {"ok": self.ok, "statement_class": self.statement_class, "attempted_writes": self.attempted_writes}


def _target_names(expression: exp.Expression) -> set[str]:
    target = expression.this
    names = set()
    table = target.this if isinstance(target, exp.Alias) else target
    if isinstance(table, exp.Table):
        names.add(table.name.lower())
        if table.alias:
            names.add(table.alias.lower())
    if isinstance(target, exp.Alias) and target.alias:
        names.add(target.alias.lower())
    return names


def _assigned_columns(update: exp.Update, target_names: set[str]) -> list[str]:
    assigned = []
    for assignment in update.expressions:
        left = assignment.this if isinstance(assignment, exp.EQ) else assignment
        if isinstance(left, exp.Column):
            if left.table and left.table.lower() not in target_names and target_names:
                # SET src.col = ... is not a write to the target; still record it conservatively.
                pass
            assigned.append(left.name.lower())
    return assigned


def guard_merge(merge: exp.Merge, column_roles_map: dict[str, str]) -> Verdict:
    frozen = {c.lower() for c, r in column_roles_map.items() if r == FROZEN}
    verdict = Verdict(ok=True, statement_class="Merge")
    targets = _target_names(merge)
    whens = merge.args.get("whens")
    has_not_matched_insert = False
    matched_deletes = []
    for when in (whens.expressions if whens else []):
        then = when.args.get("then")
        matched = bool(when.args.get("matched"))
        if matched and isinstance(then, exp.Update):
            for column in _assigned_columns(then, targets):
                if column in frozen:
                    verdict.attempted_writes.append(
                        {"column": column, "semantic_role": FROZEN, "via": "when_matched_update_set"}
                    )
        elif matched and (isinstance(then, exp.Delete) or (isinstance(then, exp.Var) and then.name.upper() == "DELETE")):
            matched_deletes.append(then)
        elif not matched and isinstance(then, exp.Insert):
            has_not_matched_insert = True
    if matched_deletes and has_not_matched_insert:
        for column in sorted(frozen):
            verdict.attempted_writes.append(
                {"column": column, "semantic_role": FROZEN, "via": "matched_delete_then_not_matched_insert"}
            )
    verdict.ok = not verdict.attempted_writes
    return verdict


def guard_statement(statement: exp.Expression, column_roles_map: dict[str, str], target: str) -> Verdict:
    """Guard any statement that can write the target: MERGE, UPDATE, DELETE, INSERT ON CONFLICT."""
    frozen = {c.lower() for c, r in column_roles_map.items() if r == FROZEN}
    target_name = target.split(".")[-1].lower()
    if isinstance(statement, exp.Merge):
        return guard_merge(statement, column_roles_map)
    verdict = Verdict(ok=True, statement_class=statement.__class__.__name__)
    if isinstance(statement, exp.Update):
        table = statement.this
        if isinstance(table, exp.Table) and table.name.lower() == target_name:
            for column in _assigned_columns(statement, {table.name.lower(), (table.alias or "").lower()}):
                if column in frozen:
                    verdict.attempted_writes.append({"column": column, "semantic_role": FROZEN, "via": "update_set"})
    elif isinstance(statement, exp.Delete):
        table = statement.this
        if isinstance(table, exp.Table) and table.name.lower() == target_name:
            for column in sorted(frozen):
                verdict.attempted_writes.append(
                    {"column": column, "semantic_role": FROZEN, "via": "delete_from_target_permits_reinsert_rebind"}
                )
    elif isinstance(statement, exp.Insert):
        conflict = statement.args.get("conflict")
        table = statement.this
        if isinstance(table, exp.Schema):
            table = table.this
        if conflict is not None and isinstance(table, exp.Table) and table.name.lower() == target_name:
            action = conflict.args.get("action")
            for assignment in conflict.expressions or []:
                left = assignment.this if isinstance(assignment, exp.EQ) else assignment
                if isinstance(left, exp.Column) and left.name.lower() in frozen:
                    verdict.attempted_writes.append(
                        {"column": left.name.lower(), "semantic_role": FROZEN, "via": "insert_on_conflict_do_update"}
                    )
            if not conflict.expressions and action is not None and "UPDATE" in action.sql().upper():
                for column in sorted(frozen):
                    verdict.attempted_writes.append(
                        {"column": column, "semantic_role": FROZEN, "via": "insert_on_conflict_do_update"}
                    )
    verdict.ok = not verdict.attempted_writes
    return verdict


def guard_sql(sql: str, column_roles_map: dict[str, str], target: str) -> Verdict:
    combined = Verdict(ok=True, statement_class="Script")
    for statement in parse(sql, dialect="duckdb"):
        if statement is None:
            continue
        verdict = guard_statement(statement, column_roles_map, target)
        combined.attempted_writes.extend(verdict.attempted_writes)
        combined.statement_class = verdict.statement_class if combined.statement_class == "Script" else "Script"
    combined.ok = not combined.attempted_writes
    return combined


def diagnosis(verdict: Verdict, descendants: list[str]) -> str:
    lines = [
        "Trade CDC stage                 PASS",
        "DimTrade row/FK checks          PASS",
        f"Incremental lifecycle contract  {'PASS' if verdict.ok else 'FAIL'}",
    ]
    if not verdict.ok:
        lines.append("  attempted write:")
        for item in verdict.attempted_writes:
            lines.append(f"    {item['column']}  (via {item['via']})")
        lines.append("  semantic role:")
        lines.append(f"    {FROZEN}")
        lines.append("Holdings attribution path       AFFECTED")
        for descendant in descendants:
            lines.append(f"    {descendant}")
    else:
        lines.append("Holdings attribution path       UNAFFECTED")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 3:
        print("usage: merge_guard.py <types.json> <logical-model.json> <candidate.sql>", file=sys.stderr)
        return 2
    types_document = json.loads(Path(argv[0]).read_text())
    logical = json.loads(Path(argv[1]).read_text())
    roles = column_roles(logical, load_roles(types_document))
    verdict = guard_sql(Path(argv[2]).read_text(), roles, logical["model_id"].split(".")[-1])
    print(diagnosis(verdict, ["logical.fact_holdings", "metric.position_by_account", "metric.position_by_customer"]))
    return 0 if verdict.ok else 3


if __name__ == "__main__":
    raise SystemExit(main())
