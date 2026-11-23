"""Write the six dashboard pages and data.js. Run export.py first.

Usage: python dashboards/build.py [--data dashboards/site/data.json] [--site dashboards/site]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ECHARTS = "https://cdn.jsdelivr.net/npm/echarts@5.5.1/dist/echarts.min.js"
REPO = "https://github.com/Saigwe/order-reliability-analytics"

PAGES = [
    ("index.html", "exec", "Executive scorecard"),
    ("otif.html", "otif", "Customer OTIF"),
    ("supplier.html", "supplier", "Supplier OTIF"),
    ("returns.html", "returns", "Returns"),
    ("ppv.html", "ppv", "Purchase price variance"),
    ("quality.html", "quality", "Data quality"),
]


def card(cid: str, title: str, sub: str, src: str = "", wide: bool = False, tall: bool = False, chart: bool = True,
         extra: str = "") -> str:
    return f'''
    <section class="card{' wide' if wide else ''}" id="{cid}">
      <header><div><h2>{title}</h2><p class="sub">{sub}</p></div>{'<button class="tbl-btn" type="button" aria-pressed="false">Table</button>' if chart else ''}</header>
      {extra}{f'<div class="chart{" tall" if tall else ""}" role="img" aria-label="{title}"></div>' if chart else ''}
      <div class="table-view" hidden></div>
      <p class="src">{src or "Source: dbt gold marts on DuckDB"}</p>
    </section>'''


def scope(text: str) -> str:
    return f'\n  <div class="filters"><span class="scope">{text}</span></div>'


GRID_OPEN, GRID_CLOSE = '\n  <div class="tiles" id="tiles"></div>\n  <div class="grid">', '\n  </div>'

BODIES = {
    "exec": ("Executive scorecard",
             "Customer service, supplier service, purchase cost and returns in one view, with the issues the other pages found.",
             scope("Orrin Electronics (fictional), three distribution centres, Nov 2025 to Oct 2026, complete months only. "
                   "Thresholds and cost rates are demo assumptions. Synthetic data.") + GRID_OPEN +
             card("ex-insights", "What needs a decision", "Ranked by severity. Each item links to the page with the detail.",
                  "Computed from every page", wide=True, chart=False, extra='<ul class="insights" id="insights"></ul>') +
             card("ex-otif", "Customer OTIF by month", "Order lines on time and in full against the original promise, and against the latest promise") +
             card("ex-sup", "Supplier OTIF by month", "Purchase-order lines received in full by the promised date") +
             card("ex-ppv", "Purchase price variance by month", "USD. Price effect at standard FX, plus the FX effect. Above zero is unfavourable") +
             card("ex-ret", "Return turnaround", "Days from receipt at the warehouse to a disposition, by month received") +
             GRID_CLOSE),
    "otif": ("Customer OTIF",
             "Where order lines miss, why, and which lines. Start with the region, then the reason, then the SKUs, then the lines.",
             scope("A line is eligible once its promise date has passed. OTIF: the quantity delivered by the promise date, across "
                   "every split shipment, covers the quantity left after cancellations. Dates are local to the shipping site.") + GRID_OPEN +
             card("ot-region", "OTIF by region and month", "Against the original promise. Darker is better", wide=True) +
             card("ot-reason", "Why lines failed, last three months", "Failed eligible lines by first failing step") +
             card("ot-source", "DC-EU: SKUs built on Meridian Semis chips against the rest", "OTIF by promise month") +
             card("ot-sku", "Pareto: failed lines by SKU, last three months", "Failed eligible lines; the table adds the cumulative share", wide=True) +
             card("ot-policy", "Which promise? DC-US against the original and the latest date", "Re-promising late lines makes OTIF look better without serving anyone sooner") +
             card("ot-carrier", "DC-AP: OTIF by carrier", "Against the original promise") +
             card("ot-drill", "The lines behind it", "DC-EU, Meridian-chip SKUs, last three months, largest shortfall first", wide=True, chart=False,
                  extra='<div id="drill" class="table-view" style="max-height:420px"></div>') +
             GRID_CLOSE),
    "supplier": ("Supplier OTIF",
                 "Inbound service from suppliers, on its own grain (purchase-order lines and receipts) and its own due date (the supplier's promise).",
                 scope("A purchase-order line is eligible once its promised date has passed. OTIF: the quantity received by the promised date covers "
                       "the quantity ordered. Synthetic data.") + GRID_OPEN +
                 card("su-heat", "Supplier OTIF by month", "Purchase-order lines on time and in full. Darker is better", wide=True) +
                 card("su-window", "Before and during the summer, by supplier", "Nov 2025 to Jun 2026 against Jul to Sep 2026") +
                 card("su-qty", "Quantity late at the promised date", "Units still owed on the promised date, by supplier and month") +
                 card("su-queue", "Escalation queue", "Suppliers ranked by units late in the last three months", wide=True, chart=False,
                      extra='<div id="queue" class="table-view"></div>') +
                 GRID_CLOSE),
    "returns": ("Returns",
                "The reverse-logistics flow: how long returned units take to reach a disposition, what is stuck, and what it is worth.",
                scope("One row per return (RMA), its lifecycle flattened from the event history. Recovery rates and handling costs per step "
                      "are demo assumptions set in dbt_project.yml.") + GRID_OPEN +
                card("re-tat", "Turnaround by disposition", "Median days from receipt to disposition, by month received") +
                card("re-p90", "P90 turnaround, all returns", "Days. The slowest tenth shows a backlog before the median moves") +
                card("re-backlog", "Open returns by stage and age", "Returns received but not yet given a disposition") +
                card("re-value", "Recovered value against handling cost", "USD, all months, by disposition") +
                card("re-family", "Where the open value sits", "Expected recoverable value of open returns, by product family", wide=True) +
                GRID_CLOSE),
    "ppv": ("Purchase price variance",
            "What purchases cost against standard, split into what suppliers charged and what currency did.",
            scope("PPV = (actual unit price in USD - standard unit cost) x quantity, per each. Positive is unfavourable (demo convention). "
                  "Price effect uses the standard FX rate; FX effect is the rest. Credit notes are excluded and shown on the quality page.") + GRID_OPEN +
            card("pv-month", "PPV by month: price and FX", "USD", wide=True) +
            card("pv-sup", "PPV by supplier", "USD, all months. Price effect and FX effect") +
            card("pv-pct", "PPV as a share of standard spend", "By supplier, last six months") +
            GRID_CLOSE),
    "quality": ("Data quality",
                "What the pipeline found and handled before any number reached a page, and the checks that run on every build.",
                scope("Each check runs in dbt (staging and singular tests) or pytest on every push. Records that fail are quarantined with "
                      "a reason code, never silently dropped.") + GRID_OPEN +
                card("dq-checks", "Checks on the latest build", "Counts from rpt_data_quality", wide=True, chart=False, extra='<div id="checks"></div>') +
                card("dq-rules", "Rules this warehouse enforces", "Where each lives", wide=True, chart=False, extra='<div id="rules"></div>') +
                GRID_CLOSE),
}


def ver(site: Path) -> str:
    h = hashlib.sha1()
    for f in ("assets/style.css", "assets/charts.js", "assets/pages.js", "data.js"):
        h.update((site / f).read_bytes())
    return h.hexdigest()[:10]


def page(key: str, v: str = "") -> str:
    title, lede, body = BODIES[key]
    nav = "".join(f'<a href="{f}"{" aria-current=page" if k == key else ""}>{label}</a>' for f, k, label in PAGES)
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Order reliability analytics</title>
<meta name="description" content="Customer and supplier OTIF, returns and purchase price variance for a fictional electronics distributor, on synthetic data.">
<link rel="stylesheet" href="assets/style.css?v={v}">
<script src="{ECHARTS}" defer></script>
<script src="assets/charts.js?v={v}" defer></script>
<script src="data.js?v={v}" defer></script>
<script src="assets/pages.js?v={v}" defer></script>
</head>
<body class="viz-root" data-page="{key}">
<div class="top"><div class="wrap">
  <div class="brand">Orrin Electronics <span>· order reliability · synthetic data</span></div>
  <nav class="tabs" aria-label="Dashboards">{nav}</nav>
  <button class="theme-btn" type="button">Dark mode</button>
</div></div>
<main class="wrap">
  <div class="page-head"><h1>{title}</h1><p>{lede}</p></div>
{body}
  <p class="footnote">Orrin Electronics and every customer, supplier, carrier and number here are invented. Demo results, not any company's figures.
  Built from dbt marts on DuckDB, rebuilt by CI on every change. Code: <a href="{REPO}">order-reliability-analytics</a>.
  Built by <a href="https://saigwe.github.io">Stanley Igwe</a>.</p>
</main>
</body>
</html>
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "site" / "data.json"))
    ap.add_argument("--site", default=str(HERE / "site"))
    a = ap.parse_args()
    site = Path(a.site)
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    (site / "data.js").write_text("window.DASH = " + json.dumps(data, separators=(",", ":")) + ";\n", encoding="utf-8")
    v = ver(site)
    for fname, key, _ in PAGES:
        (site / fname).write_text(page(key, v), encoding="utf-8", newline="\n")
    print(f"wrote {len(PAGES)} pages to {site}")


if __name__ == "__main__":
    main()
