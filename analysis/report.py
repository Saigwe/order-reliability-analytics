"""Write analysis/results.md: the headline numbers the README and decision memo quote, straight from the gold marts.

Usage: python analysis/report.py --db warehouse/orders.duckdb --out analysis/results.md
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SUMMER = "between '2026-07-01' and '2026-09-01'"


def pct(v: float) -> str:
    return f"{100 * v:.1f}%"


def usd(v: float) -> str:
    return f"${v / 1e6:.2f}M" if abs(v) >= 1e6 else f"${v / 1e3:,.0f}k"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "warehouse" / "orders.duckdb"))
    ap.add_argument("--out", default=str(ROOT / "analysis" / "results.md"))
    a = ap.parse_args()
    con = duckdb.connect(a.db, read_only=True)
    q = lambda sql: con.execute(sql).fetchone()  # noqa: E731

    lines, otif, otif_l, order_otif = q("""select sum(eligible_lines), sum(customer_otif * eligible_lines) / sum(eligible_lines),
                                                  sum(customer_otif_latest_promise * eligible_lines) / sum(eligible_lines),
                                                  avg(order_otif) from gold.rpt_exec_scorecard""")
    chip, rest = q(f"""select avg(f.is_otif_original::int) filter (where k.main_supplier_id = 'S07'),
                              avg(f.is_otif_original::int) filter (where k.main_supplier_id <> 'S07')
                       from gold.fct_order_line f join gold.dim_sku k using (sku)
                       where f.is_eligible and f.site_id = 'DC-EU' and f.promise_month {SUMMER}""")
    mer_b, mer_s = q(f"""select sum(otif_lines) filter (where promise_month < '2026-06-01')::double / sum(po_lines) filter (where promise_month < '2026-06-01'),
                                sum(otif_lines) filter (where promise_month {SUMMER})::double / sum(po_lines) filter (where promise_month {SUMMER})
                         from gold.rpt_supplier_otif_monthly where supplier_id = 'S07'""")
    us_o, us_l = q("""select sum(otif_lines_original)::double / sum(eligible_lines), sum(otif_lines_latest)::double / sum(eligible_lines)
                      from gold.rpt_customer_otif_monthly where site_id = 'DC-US' and promise_month >= '2026-03-01'""")
    disp_share, = q("""select sum(failed_lines) filter (where failure_reason like 'Late dispatch%')::double / sum(failed_lines)
                       from gold.rpt_otif_failures where promise_month > (select max(month) from gold.rpt_exec_scorecard) - interval 3 month
                         and promise_month <= (select max(month) from gold.rpt_exec_scorecard)""")
    rap, = q("""select sum(otif_lines_original)::double / sum(eligible_lines) from gold.rpt_customer_otif_monthly
                where carrier = 'Rapidline' and promise_month = '2026-02-01'""")
    ppv, cny, kes = q("""select sum(ppv_usd), sum(fx_effect_usd) filter (where currency = 'CNY' and receipt_month >= '2026-04-01'),
                                sum(price_effect_usd) filter (where supplier_id = 'S03' and receipt_month >= '2026-05-01')
                         from gold.rpt_ppv_monthly where receipt_month <= (select max(month) from gold.rpt_exec_scorecard)""")
    ref_b, ref_s = q(f"""select median(turnaround_days) filter (where received_month < '2026-07-01'),
                                median(turnaround_days) filter (where received_month {SUMMER})
                         from gold.fct_return where disposition = 'Refurbish'""")
    open_n, open_usd, old = q("""select sum(open_returns), sum(open_recoverable_usd), sum(open_returns) filter (where age_band = '30+ days')
                                 from gold.rpt_returns_backlog""")
    dq = dict(con.execute("select check_name, records from gold.rpt_data_quality").fetchall())

    rows = [
        ("Customer OTIF, 12 months, original promise", pct(otif), f"{lines:,.0f} eligible order lines"),
        ("Customer OTIF against the latest promise", pct(otif_l), "what re-promising would report"),
        ("Order OTIF (every line OTIF)", pct(order_otif), "monthly average"),
        ("DC-EU, Meridian-chip SKUs, Jul to Sep", pct(chip), f"other SKUs {pct(rest)}"),
        ("Meridian Semis supplier OTIF", f"{pct(mer_b)} to {pct(mer_s)}", "Nov to May, then Jul to Sep"),
        ("DC-US OTIF since March, original against latest promise", f"{pct(us_o)} against {pct(us_l)}", "re-promising hides misses"),
        ("Late warehouse dispatch, share of failed lines", pct(disp_share), "last three months"),
        ("Rapidline OTIF, February 2026", pct(rap), "carrier delay"),
        ("Purchase price variance, 12 months", usd(ppv), "positive is unfavourable"),
        ("CNY FX effect since April", usd(cny), "CNY about 5% above standard"),
        ("Kestrel Passives price effect since May", usd(kes), "9% rise, standard cost unchanged"),
        ("Refurbish median turnaround", f"{ref_b:.0f} to {ref_s:.0f} days", "before July, then Jul to Sep"),
        ("Open returns at extract", f"{open_n:,.0f}", f"{old:,.0f} over 30 days; {usd(open_usd)} recoverable"),
        ("Retried events dropped", f"{dq['Order events: duplicate retries dropped']:,.0f}", "kept once, at first arrival"),
        ("Warehouse double scans dropped", f"{dq['Warehouse double scans']:,.0f}", ""),
        ("Records quarantined", f"{dq['Order lines with zero quantity'] + dq['Deliveries for unknown order lines']:,.0f}", "zero quantity, unknown order line"),
    ]
    out = ["# Results from the current build", "",
           "Written by `analysis/report.py` from the gold marts on every `make dashboards`. Demo results on synthetic data.", "",
           "| Measure | Value | Note |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in rows]
    Path(a.out).write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
