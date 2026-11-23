"""Collect what the dashboard pages show into one JSON document, from the gold marts.

Usage: python dashboards/export.py --db warehouse/orders.duckdb --out dashboards/site/data.json
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import duckdb

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DONE = "(select max(month) from gold.rpt_exec_scorecard)"


def rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    out = []
    for r in cur.fetchall():
        rec = {}
        for k, v in zip(cols, r):
            if isinstance(v, date):
                v = v.isoformat()[:10]
            elif isinstance(v, float):
                v = round(v, 5)
            elif v is not None and not isinstance(v, (int, str, bool)):
                v = float(v)
            rec[k] = v
        out.append(rec)
    return out


def collect(con) -> dict:
    d: dict = {}
    d["sc"] = rows(con, "select * from gold.rpt_exec_scorecard order by month")
    d["cust"] = rows(con, f"""select promise_month as month, region, site_id, carrier, sum(eligible_lines) n, sum(on_time_lines) ot,
                                     sum(in_full_lines) inf, sum(otif_lines_original) otif, sum(otif_lines_latest) otif_latest,
                                     sum(repromised_lines) repromised
                              from gold.rpt_customer_otif_monthly where promise_month <= {DONE} group by all order by 1""")
    d["by_source"] = rows(con, f"""select f.promise_month as month, f.site_id, k.main_supplier_id supplier_id, count(*) n,
                                          sum(f.is_otif_original::int) otif
                                   from gold.fct_order_line f join gold.dim_sku k using (sku)
                                   where f.is_eligible and f.promise_month <= {DONE} group by all order by 1""")
    d["fail_reason"] = rows(con, f"""select promise_month as month, site_id, region, failure_reason, sum(failed_lines) failed
                                     from gold.rpt_otif_failures where promise_month <= {DONE} group by all""")
    d["fail_sku"] = rows(con, f"""select sku, sku_name, family, abc_band, sum(failed_lines) failed,
                                         sum(failed_lines) filter (where failure_reason = 'Short shipment (stock)') short
                                  from gold.rpt_otif_failures where promise_month <= {DONE} and promise_month > {DONE} - interval 3 month
                                  group by all order by failed desc""")
    d["drill"] = rows(con, f"""select order_line_id, order_id, region, f.sku, k.sku_name, original_promise_date, latest_promise_date,
                                      eligible_qty, delivered_by_original, delivered_qty, shipments, first_delivery_date, failure_reason
                               from gold.fct_order_line f join gold.dim_sku k using (sku)
                               where is_eligible and not is_otif_original and site_id = 'DC-EU' and k.main_supplier_id = 'S07'
                                 and promise_month > {DONE} - interval 3 month
                               order by eligible_qty - delivered_by_original desc limit 60""")
    d["drill_count"] = rows(con, f"""select count(*) n from gold.fct_order_line f join gold.dim_sku k using (sku)
                                     where is_eligible and not is_otif_original and site_id = 'DC-EU' and k.main_supplier_id = 'S07'
                                       and promise_month > {DONE} - interval 3 month""")[0]["n"]
    d["sup"] = rows(con, f"""select promise_month as month, supplier_id, supplier_name, sum(po_lines) n, sum(on_time_lines) ot,
                                    sum(in_full_lines) inf, sum(otif_lines) otif, sum(qty_late_at_promise) qty_late
                             from gold.rpt_supplier_otif_monthly where promise_month <= {DONE} group by all order by 1""")
    d["suppliers"] = rows(con, "select supplier_id, supplier_name, currency, invoice_uom from gold.dim_supplier order by 1")
    d["ppv"] = rows(con, f"""select receipt_month as month, supplier_id, currency, standard_spend_usd std, ppv_usd ppv,
                                    price_effect_usd price, fx_effect_usd fx, credit_notes_usd credits, late_invoices
                             from gold.rpt_ppv_monthly where receipt_month <= {DONE} order by 1""")
    d["ret"] = rows(con, f"""select received_month as month, disposition, count(*) as returns, sum(quantity) units,
                                    median(turnaround_days) median_days, quantile_cont(turnaround_days, 0.9) p90_days,
                                    sum(refund_usd) refund, sum(recovery_value_usd) recovery, sum(handling_cost_usd) handling
                             from gold.fct_return where received_at is not null and received_month <= {DONE}
                             group by all order by 1""")
    d["backlog"] = rows(con, """select stage, age_band, sum(open_returns) n, sum(units) units, sum(open_recoverable_usd) usd
                                from gold.rpt_returns_backlog group by all""")
    d["backlog_family"] = rows(con, """select family, stage, sum(open_returns) n, sum(open_recoverable_usd) usd
                                       from gold.rpt_returns_backlog group by all order by usd desc""")
    d["dq"] = rows(con, "select * from gold.rpt_data_quality")
    d["as_of"] = rows(con, "select max(ingested_at)::date d from silver.stg_order_events")[0]["d"]
    return d


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "warehouse" / "orders.duckdb"))
    ap.add_argument("--out", default=str(HERE / "site" / "data.json"))
    ap.add_argument("--dbt-results", default=str(ROOT / "dbt" / "target" / "run_results.json"))
    a = ap.parse_args()
    with duckdb.connect(a.db, read_only=True) as con:
        data = collect(con)
    rr = Path(a.dbt_results)
    if rr.exists():
        results = json.loads(rr.read_text(encoding="utf-8"))["results"]
        data["dbt"] = {"nodes": len(results), "passed": sum(r["status"] in ("pass", "success") for r in results),
                       "tests": sum(r["unique_id"].startswith("test.") for r in results)}
    Path(a.out).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {a.out} ({Path(a.out).stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
