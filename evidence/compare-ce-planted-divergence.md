# compare --ce against a planted one-engine divergence

Worker: Opus engineering worker, experiment-lead hat. Date 2026-09-28. Tree: 7e97414 plus the `--ce` change to
`scripts/chain_l3.py`. Both plants were made in a scratch worktree (`git worktree add --detach`), run there, and the
worktree removed. No SQL in the real tree was touched.

## Result in one paragraph

The check the brief prescribed **could not be made to fail the tempting patch, and the reason is the projection, not
`--ce`.** The planted `withdrawal_group` partition (commit 3464053's shape) is behavior-equivalent SQL on
`duckdb-native/ownership-history`: that job reads no `raw.account_cdc` (its CDC handoffs are deferred under
`L1.hole.change-effective-time`) and `ce.account_changes` has no withdrawal field, so `is_withdrawal` is the literal
`FALSE` on every row, `withdrawal_group` is 0 on every row, and the partition changes nothing on any input. `--ce
ce-withdrawn-account-v1.json` was applied (account rows 5 -> 4, because that document carries no
`ce_account_changes` and so replaces the default 428 rollover row) and correctly reported identical. The document's
own `blocked_on` already says this. The divergences 3464053 describes were measured on hand-built rows the projection
cannot receive from any anchored source.

A second plant on a surface a counterexample *can* reach does separate the two patches: bare compare `identical:
true`, `--ce` compare `identical: false` naming the row, and HEAD's `compare` (which accepted `--ce` in argparse and
silently ignored it -- exactly the tempting patch) `identical: true`.

## Plant 1 (as prescribed): withdrawal_group carry-forward boundary, native only

```diff
diff --git a/chain/l3/duckdb-native/ownership-history/account.sql b/chain/l3/duckdb-native/ownership-history/account.sql
index d9d2120..476f047 100644
--- a/chain/l3/duckdb-native/ownership-history/account.sql
+++ b/chain/l3/duckdb-native/ownership-history/account.sql
@@ -169,6 +169,12 @@ combined AS (
     UNION ALL
     SELECT * FROM constructed
 ),
+combined_grouped AS (
+    SELECT *, SUM(CASE WHEN is_withdrawal THEN 1 ELSE 0 END) OVER (
+            PARTITION BY account_number ORDER BY effective_from
+            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS withdrawal_group
+    FROM combined
+),
 carried AS (
     SELECT
         account_number,
@@ -177,7 +183,7 @@ carried AS (
         COALESCE(
             owning_customer_number,
             LAST_VALUE(owning_customer_number IGNORE NULLS) OVER (
-                PARTITION BY account_number ORDER BY effective_from
+                PARTITION BY account_number, withdrawal_group ORDER BY effective_from
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
             )
         ) AS owning_customer_number_carried,
@@ -185,12 +191,12 @@ carried AS (
         COALESCE(
             tax_treatment,
             LAST_VALUE(tax_treatment IGNORE NULLS) OVER (
-                PARTITION BY account_number ORDER BY effective_from
+                PARTITION BY account_number, withdrawal_group ORDER BY effective_from
                 ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
             )
         ) AS tax_treatment_carried,
         provenance
-    FROM combined
+    FROM combined_grouped
 ),
 account_withdrawals AS (
     SELECT account_number, MIN(effective_from) AS first_withdrawal_from
```

Bare: `chain_l3.py compare duckdb-native ownership-history --against duckdb-sqlmesh` (exit 0)
```json
{
  "job": "ownership-history",
  "targets": [
    "duckdb-native",
    "duckdb-sqlmesh"
  ],
  "both_ok": true,
  "tables": {
    "governed.customer": {
      "identical": true,
      "rows": [
        2,
        2
      ],
      "columns_match": true
    },
    "governed.account": {
      "identical": true,
      "rows": [
        5,
        5
      ],
      "columns_match": true
    }
  },
  "identical": true
}
```

With `--ce counterexamples/proposed/ce-withdrawn-account-v1.json` (exit 0)
```json
{
  "job": "ownership-history",
  "targets": [
    "duckdb-native",
    "duckdb-sqlmesh"
  ],
  "both_ok": true,
  "tables": {
    "governed.customer": {
      "identical": true,
      "rows": [
        2,
        2
      ],
      "columns_match": true
    },
    "governed.account": {
      "identical": true,
      "rows": [
        4,
        4
      ],
      "columns_match": true
    }
  },
  "counterexample": "ce.withdrawn-account-and-withdrawn-only-holding",
  "identical": true
}
```

Verdict: not observable. Stopped here on the prescribed check, per the brief.

## Plant 2 (supplementary): native drops a constructed statement that interleaves with received history

A plausible wrong policy -- "a constructed change only appends after an account's received history" -- added to the
native `constructed` CTE only (applied on top of plant 1):

```sql
    WHERE action_at > (SELECT coalesce(max(action_ts), TIMESTAMP '1900-01-01') FROM raw.customer_mgmt_action m WHERE m.ca_id = account_id)
```

Scratch counterexample (scratchpad only, not archived, not proposed): the default 428 rollover row plus one
constructed statement for account 624 at 2009-06-01, between its 2008 ADDACCT and 2010 UPDACCT.

```json
{"id": "scratch.ce-624-interleaved", "provenance": "controlled_counterexample", "status": "scratch",
 "fixture": {"ce_account_changes": [
   {"account_id": 428, "action_at": "2017-07-08 00:58:00", "provenance": "controlled_counterexample", "status_id": "ACTV", "tax_status_id": 2},
   {"account_id": 624, "action_at": "2009-06-01 12:00:00", "provenance": "controlled_counterexample", "status_id": "ACTV", "tax_status_id": 2}]}}
```

Bare compare (exit 0): `"identical": true`, account rows [5, 5] (full output equal in shape to plant 1's bare run).

With `--ce <scratch doc>` (exit 3):
```json
{
  "job": "ownership-history",
  "targets": [
    "duckdb-native",
    "duckdb-sqlmesh"
  ],
  "both_ok": true,
  "tables": {
    "governed.customer": {
      "identical": true,
      "rows": [
        2,
        2
      ],
      "columns_match": true
    },
    "governed.account": {
      "identical": false,
      "rows": [
        5,
        6
      ],
      "columns_match": true,
      "only_in": {
        "duckdb-native": [],
        "duckdb-sqlmesh": [
          [
            "624",
            "2009-06-01 12:00:00",
            "False",
            "False",
            "238",
            "ACTV",
            "2",
            "controlled_counterexample"
          ]
        ]
      }
    }
  },
  "counterexample": "scratch.ce-624-interleaved",
  "identical": false
}
```

The tempting patch -- HEAD's `compare`, which parsed `--ce` and never used it -- on the same plant and document
(exit 0): `identical: True`, rows `{'governed.customer': [2, 2], 'governed.account': [5, 5]}`.

## What this does and does not establish

- `--ce` on `compare` loads the document's rows into both engines and diffs the tables they reach; a patch that
  ignores the document fails plant 2.
- No archived or proposed counterexample reaches `ownership-history`'s withdrawal surface, and none can until an
  anchored source that carries a withdrawal is undeferred. Evidence on that surface remains zero; `--ce` does not
  change that and nothing here should be read as saying it does.
- The withdrawal-bearing documents (`raw_additions` to trade_cdc / holding_history) target `trade-lifecycle` and
  `positions`, whose `run` is refused while `ownership-history` is mid-cycle on both engines. Their `--ce` compare is
  therefore untested until a reviewer stamps ownership-history.
