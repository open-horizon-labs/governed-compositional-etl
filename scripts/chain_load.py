#!/usr/bin/env python3
"""Load raw structural anchors for the chain into DuckDB: from the bounded fixture or from DIGen batches.

Loading is structural only. Historical files carry no CDC flags; their rows load as initial
encounters (cdc_flag 'I', cdc_dsn 0) with the batch date. Constructed counterexample rows never
enter raw; they load into the ce schema for the labeled counterexample stage.
"""
from __future__ import annotations

import json
from pathlib import Path
import xml.etree.ElementTree as ET

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DDL = {
    "raw.customer_mgmt_action": "(action_type VARCHAR, action_ts TIMESTAMP, c_id BIGINT, ca_id BIGINT, ca_b_id BIGINT, ca_tax_st SMALLINT, c_tier SMALLINT)",
    "raw.account_cdc": "(cdc_flag VARCHAR, cdc_dsn BIGINT, ca_id BIGINT, ca_b_id BIGINT, c_id BIGINT, ca_name VARCHAR, ca_tax_st SMALLINT, ca_st_id VARCHAR, batch_date DATE)",
    "raw.customer_cdc": "(cdc_flag VARCHAR, cdc_dsn BIGINT, c_id BIGINT, c_st_id VARCHAR, c_tier SMALLINT, batch_date DATE)",
    "raw.trade_cdc": "(cdc_flag VARCHAR, cdc_dsn BIGINT, t_id BIGINT, t_dts TIMESTAMP, t_st_id VARCHAR, t_tt_id VARCHAR, t_is_cash BOOLEAN, t_s_symb VARCHAR, t_qty BIGINT, t_bid_price DECIMAL(8,2), t_ca_id BIGINT, t_exec_name VARCHAR, t_trade_price DECIMAL(8,2), t_chrg DECIMAL(10,2), t_comm DECIMAL(10,2), t_tax DECIMAL(10,2), batch_date DATE)",
    "raw.holding_history": "(cdc_flag VARCHAR, cdc_dsn BIGINT, hh_h_t_id BIGINT, hh_t_id BIGINT, hh_before_qty BIGINT, hh_after_qty BIGINT, batch_date DATE)",
    "raw.trade_history": "(th_t_id BIGINT, th_dts TIMESTAMP, th_st_id VARCHAR, batch_date DATE)",
    "ce.account_changes": "(account_id BIGINT, action_at TIMESTAMP, tax_status_id SMALLINT, status_id VARCHAR, provenance VARCHAR)",
}
COLUMNS = {table: [c.split()[0] for c in ddl.strip("()").split(", ")] for table, ddl in DDL.items()}


def create_schema(database: Path) -> None:
    if database.exists():
        database.unlink()
    con = duckdb.connect(str(database))
    try:
        con.execute("CREATE SCHEMA raw; CREATE SCHEMA ce; CREATE SCHEMA governed;")
        for table, ddl in DDL.items():
            con.execute(f"CREATE TABLE {table} {ddl}")
    finally:
        con.close()


def _insert(con, table: str, rows: list[dict]) -> None:
    cols = COLUMNS[table]
    for row in rows:
        con.execute(f"INSERT INTO {table} VALUES ({', '.join('?' for _ in cols)})", [row.get(c) for c in cols])


def load_fixture(database: Path, fixture: dict, phase: str, ce_changes: list[dict] | None = None, raw_additions: dict[str, list[dict]] | None = None) -> None:
    """Rebuild raw from the fixture for one phase. CE rows load only when the phase applies the counterexample."""
    spec = fixture["phases"][phase]
    batches = {fixture["batch_dates"][b] for b in spec["include_batches"]}
    create_schema(database)
    con = duckdb.connect(str(database))
    try:
        _insert(con, "raw.customer_mgmt_action", fixture["raw"]["customer_mgmt_action"])
        for table in ("account_cdc", "customer_cdc", "trade_cdc", "holding_history", "trade_history"):
            _insert(con, f"raw.{table}", [r for r in fixture["raw"].get(table, []) if r["batch_date"] in batches])
        if spec["apply_counterexample"] and ce_changes:
            for row in ce_changes:
                if row.get("provenance") != "controlled_counterexample":
                    raise ValueError("counterexample rows must be labeled controlled_counterexample")
            _insert(con, "ce.account_changes", ce_changes)
        if spec["apply_counterexample"] and raw_additions:
            _insert_raw_additions(con, raw_additions, batches)
    finally:
        con.close()


def _insert_raw_additions(con, raw_additions: dict[str, list[dict]], batches: set[str]) -> None:
    """Constructed received reports a counterexample adds to raw tables. Raw tables carry no provenance column, so the
    label lives on the counterexample document; rows outside the phase's batches are not loaded."""
    for table, rows in raw_additions.items():
        if f"raw.{table}" not in COLUMNS:
            raise ValueError(f"counterexample adds rows to unknown raw table {table}")
        _insert(con, f"raw.{table}", [r for r in rows if r.get("batch_date") in batches])


def reload_sources(database: Path, fixture: dict, phase: str, ce_changes: list[dict] | None = None, raw_additions: dict[str, list[dict]] | None = None) -> None:
    """Replace raw.* and ce.* tables for a phase, keeping governed.* intact: the second half of a two-phase simulation."""
    spec = fixture["phases"][phase]
    batches = {fixture["batch_dates"][b] for b in spec["include_batches"]}
    con = duckdb.connect(str(database))
    try:
        for table, ddl in DDL.items():
            con.execute(f"DROP TABLE IF EXISTS {table}")
            con.execute(f"CREATE TABLE {table} {ddl}")
        _insert(con, "raw.customer_mgmt_action", fixture["raw"]["customer_mgmt_action"])
        for table in ("account_cdc", "customer_cdc", "trade_cdc", "holding_history", "trade_history"):
            _insert(con, f"raw.{table}", [r for r in fixture["raw"].get(table, []) if r["batch_date"] in batches])
        if spec["apply_counterexample"] and ce_changes:
            _insert(con, "ce.account_changes", ce_changes)
        if spec["apply_counterexample"] and raw_additions:
            _insert_raw_additions(con, raw_additions, batches)
    finally:
        con.close()


def parse_customer_mgmt(path: Path):
    for _, element in ET.iterparse(str(path), events=("end",)):
        if not element.tag.endswith("Action"):
            continue
        customer = element.find("Customer")
        if customer is not None:
            account = customer.find("Account")
            yield {
                "action_type": element.get("ActionType"),
                "action_ts": element.get("ActionTS").replace("T", " "),
                "c_id": int(customer.get("C_ID")),
                "ca_id": int(account.get("CA_ID")) if account is not None and account.get("CA_ID") else None,
                "ca_b_id": int(account.findtext("CA_B_ID")) if account is not None and account.findtext("CA_B_ID") else None,
                "ca_tax_st": int(account.get("CA_TAX_ST")) if account is not None and account.get("CA_TAX_ST") else None,
                "c_tier": int(customer.get("C_TIER")) if customer.get("C_TIER") else None,
            }
        element.clear()


def load_digen(database: Path, batches_root: Path, up_to_batch: int) -> dict:
    """Load DIGen Batch1..N structural anchors. Returns row counts. Never reads counterexamples."""
    create_schema(database)
    con = duckdb.connect(str(database))
    counts = {}
    try:
        b1 = batches_root / "Batch1"
        batch_date = (b1 / "BatchDate.txt").read_text().strip()
        con.executemany(
            "INSERT INTO raw.customer_mgmt_action VALUES (?,?,?,?,?,?,?)",
            [[r[c] for c in COLUMNS["raw.customer_mgmt_action"]] for r in parse_customer_mgmt(b1 / "CustomerMgmt.xml")],
        )
        con.execute(f"""INSERT INTO raw.trade_cdc SELECT 'I', 0, *, DATE '{batch_date}' FROM read_csv('{(b1 / 'Trade.txt').as_posix()}', delim='|', header=false,
            columns={{'t_id':'BIGINT','t_dts':'TIMESTAMP','t_st_id':'VARCHAR','t_tt_id':'VARCHAR','t_is_cash':'BOOLEAN','t_s_symb':'VARCHAR','t_qty':'BIGINT','t_bid_price':'DECIMAL(8,2)','t_ca_id':'BIGINT','t_exec_name':'VARCHAR','t_trade_price':'DECIMAL(8,2)','t_chrg':'DECIMAL(10,2)','t_comm':'DECIMAL(10,2)','t_tax':'DECIMAL(10,2)'}})""")
        con.execute(f"""INSERT INTO raw.holding_history SELECT NULL, NULL, *, DATE '{batch_date}' FROM read_csv('{(b1 / 'HoldingHistory.txt').as_posix()}', delim='|', header=false,
            columns={{'hh_h_t_id':'BIGINT','hh_t_id':'BIGINT','hh_before_qty':'BIGINT','hh_after_qty':'BIGINT'}})""")
        con.execute(f"""INSERT INTO raw.trade_history SELECT *, DATE '{batch_date}' FROM read_csv('{(b1 / 'TradeHistory.txt').as_posix()}', delim='|', header=false,
            columns={{'th_t_id':'BIGINT','th_dts':'TIMESTAMP','th_st_id':'VARCHAR'}})""")
        for n in range(2, up_to_batch + 1):
            b = batches_root / f"Batch{n}"
            batch_date = (b / "BatchDate.txt").read_text().strip()
            con.execute(f"""INSERT INTO raw.account_cdc SELECT *, DATE '{batch_date}' FROM read_csv('{(b / 'Account.txt').as_posix()}', delim='|', header=false,
                columns={{'cdc_flag':'VARCHAR','cdc_dsn':'BIGINT','ca_id':'BIGINT','ca_b_id':'BIGINT','c_id':'BIGINT','ca_name':'VARCHAR','ca_tax_st':'SMALLINT','ca_st_id':'VARCHAR'}})""")
            con.execute(f"""INSERT INTO raw.customer_cdc SELECT cdc_flag, cdc_dsn, c_id, c_st_id, c_tier, DATE '{batch_date}' FROM read_csv('{(b / 'Customer.txt').as_posix()}', delim='|', header=false, all_varchar=true,
                columns={{'cdc_flag':'VARCHAR','cdc_dsn':'VARCHAR','c_id':'VARCHAR','c_tax_id':'VARCHAR','c_st_id':'VARCHAR','c_l_name':'VARCHAR','c_f_name':'VARCHAR','c_m_name':'VARCHAR','c_gndr':'VARCHAR','c_tier':'VARCHAR','c_dob':'VARCHAR','c_adline1':'VARCHAR','c_adline2':'VARCHAR','c_zipcode':'VARCHAR','c_city':'VARCHAR','c_state_prov':'VARCHAR','c_ctry':'VARCHAR','c_ctry_1':'VARCHAR','c_area_1':'VARCHAR','c_local_1':'VARCHAR','c_ext_1':'VARCHAR','c_ctry_2':'VARCHAR','c_area_2':'VARCHAR','c_local_2':'VARCHAR','c_ext_2':'VARCHAR','c_ctry_3':'VARCHAR','c_area_3':'VARCHAR','c_local_3':'VARCHAR','c_ext_3':'VARCHAR','c_email_1':'VARCHAR','c_email_2':'VARCHAR','c_lcl_tx_id':'VARCHAR','c_nat_tx_id':'VARCHAR'}}, ignore_errors=true)""")
            con.execute(f"""INSERT INTO raw.trade_cdc SELECT *, DATE '{batch_date}' FROM read_csv('{(b / 'Trade.txt').as_posix()}', delim='|', header=false,
                columns={{'cdc_flag':'VARCHAR','cdc_dsn':'BIGINT','t_id':'BIGINT','t_dts':'TIMESTAMP','t_st_id':'VARCHAR','t_tt_id':'VARCHAR','t_is_cash':'BOOLEAN','t_s_symb':'VARCHAR','t_qty':'BIGINT','t_bid_price':'DECIMAL(8,2)','t_ca_id':'BIGINT','t_exec_name':'VARCHAR','t_trade_price':'DECIMAL(8,2)','t_chrg':'DECIMAL(10,2)','t_comm':'DECIMAL(10,2)','t_tax':'DECIMAL(10,2)'}})""")
            con.execute(f"""INSERT INTO raw.holding_history SELECT *, DATE '{batch_date}' FROM read_csv('{(b / 'HoldingHistory.txt').as_posix()}', delim='|', header=false,
                columns={{'cdc_flag':'VARCHAR','cdc_dsn':'BIGINT','hh_h_t_id':'BIGINT','hh_t_id':'BIGINT','hh_before_qty':'BIGINT','hh_after_qty':'BIGINT'}})""")
        for table in DDL:
            counts[table] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    finally:
        con.close()
    return counts


if __name__ == "__main__":
    import sys
    db = ROOT / "build/tpcdi-chain.duckdb"
    print(json.dumps(load_digen(db, ROOT / "raw/generated/tpcdi-sf3-review", int(sys.argv[1]) if len(sys.argv) > 1 else 2), indent=2))
