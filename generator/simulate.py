"""Synthetic order, supply, warehouse and returns event data for Orrin Electronics, a fictional consumer-electronics
company with three distribution centres, 1 Nov 2025 to 31 Oct 2026.

Everything is invented. Source tables are immutable event logs, written the way they arrive: with retries (duplicate
event ids), late-arriving events, duplicate warehouse scans and a few deliberately bad records. Known problems are
planted so every report can be checked against data/raw/answer_key.json, which no model reads.

Usage: python generator/simulate.py --out data/raw [--seed 11]
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

START, END = date(2025, 11, 1), date(2026, 10, 31)
AS_OF = datetime(2026, 11, 3, 6, 0)          # extract time: events after this have not arrived yet

SITES = pd.DataFrame([
    ("DC-US", "Memphis DC", "Americas", -6),
    ("DC-EU", "Venlo DC", "EMEA", 1),
    ("DC-AP", "Singapore DC", "APAC", 8),
], columns=["site_id", "site_name", "site_region", "utc_offset_hours"])
REGIONS = [("North America", "DC-US", 0.40), ("UK & Ireland", "DC-EU", 0.14), ("Central Europe", "DC-EU", 0.16),
           ("Southern Europe", "DC-EU", 0.10), ("APAC", "DC-AP", 0.20)]
CARRIERS = {"DC-US": [("Pinecrest Freight", 2), ("Atlas Ground", 3)], "DC-EU": [("EuroLink", 2), ("SwiftHaul", 3)],
            "DC-AP": [("Rapidline", 3), ("Straits Logistics", 2)]}
FAMILIES = [("Headphones", 12, 120), ("Earbuds", 12, 80), ("Speakers", 14, 150), ("Soundbars", 8, 320),
            ("Accessories", 14, 25)]
SUPPLIERS = pd.DataFrame([
    ("S01", "Harmon Contract Mfg", "CNY", "EA"), ("S02", "Penang Acoustic Works", "USD", "EA"),
    ("S03", "Kestrel Passives", "USD", "C100"), ("S04", "Lumen Packaging", "EUR", "EA"),
    ("S05", "Coralis Batteries", "JPY", "EA"), ("S06", "Tessa Plastics", "CNY", "EA"),
    ("S07", "Meridian Semis", "USD", "EA"), ("S08", "Nordvik Cables", "EUR", "EA"),
], columns=["supplier_id", "supplier_name", "currency", "invoice_uom"])
STD_FX = {"USD": 1.0, "EUR": 1.08, "CNY": 0.139, "JPY": 0.0067}   # USD per unit of currency, the 2026 standard

# Planted answers -----------------------------------------------------------------------------------------------
SHORTAGE = ("S07", "DC-EU", date(2026, 6, 15), date(2026, 9, 30))   # chip shortage -> split deliveries in EU
REPROMISE = ("DC-US", date(2026, 3, 1), 0.16)                       # US DC re-promises lines it will miss
CARRIER_DELAY = ("Rapidline", date(2026, 1, 26), date(2026, 3, 8))  # peak-season transit delays
PRICE_RISE = ("S03", date(2026, 5, 1), 0.09)                        # passive components +9%, standard unchanged
INSPECTION_BACKLOG = (date(2026, 7, 1), "Refurbish")                # returns centre falls behind on refurbishment


def utc(d: date, hour: float, offset: int) -> datetime:
    """Local wall-clock time at a site -> UTC (fixed offsets; daylight saving ignored on purpose)."""
    return datetime(d.year, d.month, d.day) + timedelta(hours=hour - offset)


def simulate(out: Path, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    out.mkdir(parents=True, exist_ok=True)
    days = pd.date_range(START, END, freq="D").date

    # Dimensions --------------------------------------------------------------------------------------------------
    skus, k = [], 1000
    for fam, n, price in FAMILIES:
        for j in range(n):
            k += 1
            skus.append((f"MAT-{k}", f"{fam} {chr(65 + j)}{j + 1}", fam, round(price * rng.uniform(0.5, 1.6), 2)))
    skus = pd.DataFrame(skus, columns=["sku", "sku_name", "family", "unit_value_usd"])
    skus["standard_cost_usd"] = (skus.unit_value_usd * rng.uniform(0.42, 0.55, len(skus))).round(2)
    skus["demand_weight"] = rng.lognormal(0, 1.0, len(skus))
    chip_skus = list(skus[skus.family.isin(["Earbuds", "Speakers"])].sort_values("demand_weight", ascending=False).sku.iloc[[0, 2, 3, 5, 8]])
    skus["main_supplier"] = np.where(skus.sku.isin(chip_skus), "S07", rng.choice(["S01", "S02", "S06"], len(skus)))
    cust = []
    for i in range(240):
        reg, site, _ = REGIONS[int(rng.choice(len(REGIONS), p=[r[2] for r in REGIONS]))]
        cust.append((f"C{i + 1:04d}", f"Customer {i + 1:04d}", reg, site, str(rng.choice(["Retail", "Online", "Distributor"]))))
    customers = pd.DataFrame(cust, columns=["customer_id", "customer_name", "region", "site_id", "channel"])
    off = dict(zip(SITES.site_id, SITES.utc_offset_hours))

    # Customer order lines and their events ---------------------------------------------------------------------------
    ev, lines, shipments, scans = [], [], [], []
    ev_n = 0
    p_sku = (skus.demand_weight / skus.demand_weight.sum()).to_numpy()
    for d in days:
        n_orders = int(rng.poisson(130 * (1.4 if d.month in (11, 12) else 1.0)))
        order_lines_today = [(o, l) for o in range(n_orders) for l in range(int(rng.choice([1, 1, 2, 2, 3, 4])))]
        ocust = rng.integers(0, len(customers), n_orders)
        sidx = rng.choice(len(skus), len(order_lines_today), p=p_sku)
        for i, (o, l) in enumerate(order_lines_today):
            c = customers.iloc[ocust[o]]
            s = skus.iloc[sidx[i]]
            site = c.site_id
            order_id = f"SO{d:%y%m%d}{o:04d}"
            line_id = f"{order_id}-{l + 1}"
            qty = int(rng.integers(1, 40)) if rng.random() > 0.0003 else 0          # a few zero-quantity lines
            ordered_at = utc(d, rng.uniform(8, 18), off[site])
            promise = d + timedelta(days=int(rng.integers(4, 9)))
            lines.append((line_id, order_id, c.customer_id, s.sku, site, qty, ordered_at, promise))
            ev_n += 1
            ev.append((f"E{ev_n:08d}", "order_line_created", line_id, ordered_at, qty, promise, None))
            if qty == 0:
                continue
            # cancellations
            r = rng.random()
            cancelled = qty if r < 0.02 else (int(qty * rng.uniform(0.2, 0.6)) if r < 0.03 else 0)
            if cancelled:
                ev_n += 1
                ev.append((f"E{ev_n:08d}", "line_cancelled", line_id, ordered_at + timedelta(hours=rng.uniform(2, 48)), cancelled, None, None))
            eligible = qty - cancelled
            if eligible <= 0:
                continue
            # fulfilment plan: dispatch lag, transit, shortage
            carrier, transit_std = CARRIERS[site][int(rng.random() < 0.45)]
            dispatch = d + timedelta(days=int(rng.choice([1, 1, 2, 2, 3])))
            transit = transit_std + int(rng.choice([0, 0, 0, 1]))
            if rng.random() < 0.035:
                dispatch += timedelta(days=int(rng.integers(2, 6)))                 # ordinary warehouse slips
            if carrier == CARRIER_DELAY[0] and CARRIER_DELAY[1] <= dispatch <= CARRIER_DELAY[2] and rng.random() < 0.45:
                transit += int(rng.integers(2, 6))
            parts = [(eligible, dispatch, transit)]
            short = (s.main_supplier == SHORTAGE[0] and site == SHORTAGE[1] and SHORTAGE[2] <= d <= SHORTAGE[3]
                     and rng.random() < 0.6)
            if not short and rng.random() < 0.012:
                short = True                                                        # ordinary stock-outs
            if short and eligible > 1:
                first = max(1, int(eligible * rng.uniform(0.3, 0.8)))
                parts = [(first, dispatch, transit), (eligible - first, promise + timedelta(days=int(rng.integers(4, 21))), transit_std)]
            arrival = parts[-1][1] + timedelta(days=parts[-1][2])
            # re-promising: the US DC moves the promise when it knows it will miss
            if site == REPROMISE[0] and d >= REPROMISE[1] and arrival > promise and rng.random() < 0.85:
                new_p = arrival + timedelta(days=int(rng.integers(0, 2)))
                ev_n += 1
                ev.append((f"E{ev_n:08d}", "promise_changed", line_id, utc(dispatch - timedelta(days=1), 10, off[site]), None, new_p, None))
            elif arrival > promise and rng.random() < 0.08:
                ev_n += 1
                ev.append((f"E{ev_n:08d}", "promise_changed", line_id, utc(d + timedelta(days=1), 11, off[site]), None,
                           arrival + timedelta(days=1), None))
            for j, (q, disp, tr) in enumerate(parts):
                shp = f"SH-{line_id}-{j + 1}"
                disp_ts = utc(disp, rng.uniform(9, 20), off[site])
                # deliveries late in the local evening: UTC date differs from local date
                deliv_ts = utc(disp + timedelta(days=tr), rng.uniform(8, 23.8), off[site])
                shipments.append((shp, line_id, site, carrier))
                for st in ("picked", "packed", "dispatched"):
                    t = disp_ts - timedelta(hours={"picked": 5, "packed": 2, "dispatched": 0}[st])
                    scans.append((shp, st, t))
                    if rng.random() < 0.05:
                        scans.append((shp, st, t + timedelta(seconds=int(rng.integers(1, 90)))))   # double scan
                ev_n += 1
                ev.append((f"E{ev_n:08d}", "shipment_delivered", line_id, deliv_ts, q, None, shp))
    # orphan deliveries: proof of delivery for lines the order system never sent
    for j in range(12):
        ev_n += 1
        ev.append((f"E{ev_n:08d}", "shipment_delivered", f"SO-UNKNOWN-{j}", utc(days[int(rng.integers(30, 300))], 12, 1), 5, None, f"SH-UNKNOWN-{j}"))

    events = pd.DataFrame(ev, columns=["event_id", "event_type", "order_line_id", "event_ts_utc", "quantity", "promise_date", "shipment_id"])
    lag_h = rng.gamma(2, 2, len(events))
    late = rng.random(len(events)) < 0.03
    lag_h = np.where(late, rng.uniform(48, 240, len(events)), lag_h)                 # late-arriving events
    events["ingested_at"] = events.event_ts_utc + pd.to_timedelta(lag_h, unit="h")
    dup = events.sample(frac=0.02, random_state=seed).copy()                         # retried deliveries
    dup["ingested_at"] = dup.ingested_at + pd.to_timedelta(rng.uniform(0.1, 30, len(dup)), unit="h")
    events = pd.concat([events, dup]).sort_values("ingested_at")
    events = events[events.ingested_at <= AS_OF]                                     # not arrived yet at extract time
    events["batch_date"] = events.ingested_at.dt.date
    order_lines = pd.DataFrame(lines, columns=["order_line_id", "order_id", "customer_id", "sku", "site_id", "ordered_qty", "ordered_at_utc", "original_promise_date"])
    ship = pd.DataFrame(shipments, columns=["shipment_id", "order_line_id", "site_id", "carrier"])
    sc = pd.DataFrame(scans, columns=["shipment_id", "scan_type", "scanned_at_utc"])
    sc = sc[sc.scanned_at_utc <= AS_OF]

    # Supplier purchase orders, receipts and invoices -------------------------------------------------------------
    po, rec, inv = [], [], []
    pk = 0
    fx_days = pd.date_range(START - timedelta(days=60), END + timedelta(days=60), freq="D")
    fx = []
    for cur, std in STD_FX.items():
        walk = np.cumsum(rng.normal(0, 0.001, len(fx_days)))
        drift = np.where(fx_days >= pd.Timestamp("2026-04-01"), 0.05, 0.0) if cur == "CNY" else 0.0
        rates = std * np.exp(walk - walk[0] + drift) if cur != "USD" else np.ones(len(fx_days))
        fx += [(dd.date(), cur, float(rr)) for dd, rr in zip(fx_days, rates)]
    fx = pd.DataFrame(fx, columns=["rate_date", "currency", "usd_per_unit"])
    fxd = {(r.rate_date, r.currency): r.usd_per_unit for r in fx.itertuples()}
    comp_cost = {"S03": 0.42, "S04": 0.65, "S05": 2.2, "S07": 4.8, "S08": 0.9}
    for w in pd.date_range(START - timedelta(days=28), END, freq="W-MON").date:
        for sup in SUPPLIERS.itertuples():
            for site in SITES.site_id:
                for _ in range(int(rng.integers(1, 4))):
                    pk += 1
                    if sup.supplier_id in ("S01", "S02", "S06"):
                        sku_row = skus[skus.main_supplier == sup.supplier_id].sample(1, random_state=int(rng.integers(1e9))).iloc[0]
                        item, std, qty = sku_row.sku, float(sku_row.standard_cost_usd), int(rng.integers(200, 2000))
                    else:
                        item, std, qty = f"COMP-{sup.supplier_id}", comp_cost[sup.supplier_id], int(rng.integers(2000, 30000))
                    promised = w + timedelta(days=int(rng.integers(21, 35)))
                    po_line = f"PO{pk:06d}-1"
                    po.append((po_line, sup.supplier_id, site, item, w, promised, qty, std))
                    shortage = sup.supplier_id == SHORTAGE[0] and site == SHORTAGE[1] and SHORTAGE[2] - timedelta(days=30) <= promised <= SHORTAGE[3]
                    if shortage:
                        splits = [(0.55, int(rng.integers(8, 25))), (0.45, int(rng.integers(20, 40)))]
                    elif rng.random() < 0.06:
                        splits = [(0.7, int(rng.integers(-2, 3))), (0.3, int(rng.integers(5, 15)))]
                    else:
                        splits = [(1.0, int(rng.choice([-3, -2, -1, -1, 0, 0, 0, 0, 0, 0, 0, 3])))]
                    left = qty
                    for j, (share, delay) in enumerate(splits):
                        q = left if j == len(splits) - 1 else int(qty * share)
                        left -= q
                        rd = promised + timedelta(days=delay)
                        if rd > END:
                            continue
                        rec.append((f"GR-{po_line}-{j + 1}", po_line, rd, q))
                        # invoice: supplier currency and unit of measure
                        price_usd = std * rng.normal(1.0, 0.012)
                        if sup.supplier_id == PRICE_RISE[0] and rd >= PRICE_RISE[1]:
                            price_usd *= 1 + PRICE_RISE[2]
                        inv_date = rd + timedelta(days=int(rng.integers(1, 12) if rng.random() > 0.05 else rng.integers(35, 70)))
                        price_local = price_usd / STD_FX[sup.currency]          # suppliers quote at the standard rate
                        if sup.invoice_uom == "C100":
                            price_local *= 100
                        inv_qty = q / 100 if sup.invoice_uom == "C100" else q
                        inv.append((f"INV-{po_line}-{j + 1}", po_line, f"GR-{po_line}-{j + 1}", inv_date, sup.currency, sup.invoice_uom,
                                    round(inv_qty, 2), round(price_local, 4)))
                        if rng.random() < 0.01:                                  # credit note for damaged goods
                            inv.append((f"CRN-{po_line}-{j + 1}", po_line, f"GR-{po_line}-{j + 1}", inv_date + timedelta(days=9),
                                        sup.currency, sup.invoice_uom, -round(inv_qty * 0.1, 2), round(price_local, 4)))
    purchase_orders = pd.DataFrame(po, columns=["po_line_id", "supplier_id", "site_id", "item", "order_date", "promised_date", "ordered_qty", "standard_unit_cost_usd"])
    receipts = pd.DataFrame(rec, columns=["receipt_id", "po_line_id", "received_date", "received_qty"])
    invoices = pd.DataFrame(inv, columns=["invoice_line_id", "po_line_id", "receipt_id", "invoice_date", "currency", "uom", "invoice_qty", "unit_price_local"])
    invoices = invoices[invoices.invoice_date <= AS_OF.date()]

    # Returns lifecycle -------------------------------------------------------------------------------------------
    deliv = events[(events.event_type == "shipment_delivered") & ~events.order_line_id.str.startswith("SO-UNKNOWN")] \
        .drop_duplicates("event_id").merge(order_lines[["order_line_id", "sku", "site_id", "customer_id"]], on="order_line_id")
    deliv = deliv.merge(skus[["sku", "family", "unit_value_usd", "standard_cost_usd"]], on="sku")
    ret = deliv[rng.random(len(deliv)) < 0.045].copy()
    rev, rk = [], 0
    for r in ret.itertuples():
        rk += 1
        rma = f"RMA{rk:06d}"
        q = max(1, int(r.quantity * rng.uniform(0.05, 0.3)))
        t0 = r.event_ts_utc + timedelta(days=float(rng.uniform(2, 25)))
        add = lambda et, t, extra=None: rev.append((rma, r.order_line_id, r.sku, r.site_id, et, t, q, extra))
        add("authorised", t0)
        t1 = t0 + timedelta(days=float(rng.uniform(2, 9)))
        if rng.random() < 0.06:
            continue                                                              # never sent back
        add("received", t1)
        disp = str(rng.choice(["Restock", "Refurbish", "Recycle", "Return to vendor"], p=[0.45, 0.30, 0.15, 0.10]))
        lag = float(rng.uniform(1, 6))
        if disp == INSPECTION_BACKLOG[1] and t1.date() >= INSPECTION_BACKLOG[0]:
            lag = float(rng.uniform(18, 55))
        t2 = t1 + timedelta(days=lag)
        refund_share = 1.0 if rng.random() > 0.05 else float(rng.uniform(0.3, 0.8))   # partial refunds
        add("refunded", t1 + timedelta(days=float(rng.uniform(0.5, 3))), round(q * r.unit_value_usd * refund_share, 2))
        add("inspected", t2)
        if rng.random() < 0.012:
            continue                                                              # disposition never recorded
        add("disposition_" + disp.lower().replace(" ", "_"), t2 + timedelta(days=float(rng.uniform(0.2, 3))))
    returns = pd.DataFrame(rev, columns=["rma_id", "order_line_id", "sku", "site_id", "event_type", "event_ts_utc", "quantity", "refund_usd"])
    returns = returns[returns.event_ts_utc <= AS_OF]
    dup_r = returns[returns.event_type == "authorised"].sample(frac=0.005, random_state=seed)   # duplicate RMAs
    returns = pd.concat([returns, dup_r]).reset_index(drop=True)
    returns["return_event_id"] = [f"R{i:08d}" for i in range(1, len(returns) + 1)]

    tables = {"order_lines": order_lines, "order_events": events, "shipments": ship, "warehouse_scans": sc,
              "skus": skus.drop(columns=["demand_weight", "main_supplier"]),
              "sku_sources": skus[["sku", "main_supplier"]].rename(columns={"main_supplier": "supplier_id"}),
              "customers": customers, "sites": SITES, "suppliers": SUPPLIERS,
              "carriers": pd.DataFrame([(c, s, t) for s, cs in CARRIERS.items() for c, t in cs], columns=["carrier", "site_id", "standard_transit_days"]),
              "purchase_orders": purchase_orders, "receipts": receipts, "invoices": invoices, "fx_rates": fx,
              "standard_fx": pd.DataFrame(list(STD_FX.items()), columns=["currency", "usd_per_unit"]), "return_events": returns}
    for name, df in tables.items():
        df.to_parquet(out / f"{name}.parquet", index=False)
        print(f"{name:<18}{len(df):>10,} rows")
    key = {"shortage": {"supplier": SHORTAGE[0], "site": SHORTAGE[1], "from": str(SHORTAGE[2]), "to": str(SHORTAGE[3]),
                        "skus": chip_skus, "regions_hit": ["UK & Ireland", "Central Europe", "Southern Europe"]},
           "repromise": {"site": REPROMISE[0], "from": str(REPROMISE[1])},
           "carrier_delay": {"carrier": CARRIER_DELAY[0], "from": str(CARRIER_DELAY[1]), "to": str(CARRIER_DELAY[2])},
           "price_rise": {"supplier": PRICE_RISE[0], "from": str(PRICE_RISE[1]), "rise": PRICE_RISE[2]},
           "fx_move": {"currency": "CNY", "from": "2026-04-01", "rise": 0.05},
           "inspection_backlog": {"from": str(INSPECTION_BACKLOG[0]), "disposition": INSPECTION_BACKLOG[1]},
           "bad_records": {"zero_qty_lines": int((order_lines.ordered_qty == 0).sum()), "orphan_deliveries": 12}}
    (out / "answer_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    return key


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="data/raw")
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()
    simulate(Path(a.out), a.seed)
