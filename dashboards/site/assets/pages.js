/* Page renderers. Data: window.DASH (data.js, written by dashboards/build.py). */
(function () {
  "use strict";
  const D = window.DASH;
  const { line, bar, heatmap, card, table, fmt, esc } = window.Viz;
  const sum = (a) => a.reduce((x, y) => x + (y || 0), 0);
  const uniq = (a) => [...new Set(a)];
  const mon = (s) => new Date(s + "T00:00:00").toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
  const usdK = (v) => v == null ? "–" : (v < 0 ? "-$" : "$") + (Math.abs(v) >= 1e6 ? (Math.abs(v) / 1e6).toFixed(2) + "M" : Math.abs(v / 1e3).toFixed(0) + "k");
  const ratio = (a, b) => (b ? a / b : null);
  const SUP = Object.fromEntries(D.suppliers.map((s) => [s.supplier_id, s.supplier_name]));
  const months = D.sc.map((r) => r.month);
  const last3 = months.slice(-3);
  const SUMMER = ["2026-07-01", "2026-08-01", "2026-09-01"];
  const rate = (rows, k = "otif", n = "n") => ratio(sum(rows.map((r) => r[k])), sum(rows.map((r) => r[n])));
  const byMonth = (rows, pred, k = "otif", n = "n") => months.map((m) => rate(rows.filter((r) => r.month === m && pred(r)), k, n));

  function tiles(list) {
    const el = document.getElementById("tiles");
    if (!el) return;
    el.replaceChildren(...list.map((t) => {
      const d = document.createElement("div"); d.className = "tile";
      const k = document.createElement("div"); k.className = "k"; k.textContent = t.k;
      const v = document.createElement("div"); v.className = "v"; v.textContent = t.v;
      d.append(k, v);
      if (t.d) { const s = document.createElement("div"); s.className = "d"; s.textContent = t.d; d.append(s); }
      return d;
    }));
  }

  /* ---------- facts shared by the scorecard and the pages ---------- */
  function facts() {
    const f = {};
    const C = D.cust;
    const reg = uniq(C.map((r) => r.region));
    f.region = reg.map((g) => ({ g, before: rate(C.filter((r) => r.region === g && r.month < "2026-06-01")), summer: rate(C.filter((r) => r.region === g && SUMMER.includes(r.month))) }))
      .sort((a, b) => (a.summer - a.before) - (b.summer - b.before));
    const eu = D.by_source.filter((r) => r.site_id === "DC-EU" && SUMMER.includes(r.month));
    f.chip = rate(eu.filter((r) => r.supplier_id === "S07")); f.nonChip = rate(eu.filter((r) => r.supplier_id !== "S07"));
    const fr = D.fail_reason.filter((r) => r.site_id === "DC-EU" && SUMMER.includes(r.month));
    f.shortShare = ratio(sum(fr.filter((r) => r.failure_reason.startsWith("Short")).map((r) => r.failed)), sum(fr.map((r) => r.failed)));
    const sw = (s, pred) => rate(D.sup.filter((r) => r.supplier_id === s && pred(r.month)));
    f.mer = { before: sw("S07", (m) => m < "2026-06-01"), summer: sw("S07", (m) => SUMMER.includes(m)) };
    const us = C.filter((r) => r.site_id === "DC-US" && r.month >= "2026-03-01");
    f.us = { o: rate(us), l: rate(us, "otif_latest"), rep: ratio(sum(us.map((r) => r.repromised)), sum(us.map((r) => r.n))) };
    const ap = C.filter((r) => r.site_id === "DC-AP" && r.month === "2026-02-01");
    f.rap = rate(ap.filter((r) => r.carrier === "Rapidline")); f.str = rate(ap.filter((r) => r.carrier !== "Rapidline"));
    const pv = (pred, k) => sum(D.ppv.filter(pred).map((r) => r[k]));
    f.s03 = pv((r) => r.supplier_id === "S03" && r.month >= "2026-05-01", "price");
    f.cny = pv((r) => r.currency === "CNY" && r.month >= "2026-04-01", "fx");
    f.jpy = pv((r) => r.currency === "JPY", "fx");
    f.ppvTotal = pv(() => true, "ppv");
    const rf = D.ret.filter((r) => r.disposition === "Refurbish");
    const med = (rows) => { const n = sum(rows.map((r) => r.returns)); return ratio(sum(rows.map((r) => r.median_days * r.returns)), n); };
    f.refBefore = med(rf.filter((r) => r.month < "2026-07-01")); f.refSummer = med(rf.filter((r) => SUMMER.includes(r.month)));
    const f3 = D.fail_reason.filter((r) => last3.includes(r.month)), tf = sum(f3.map((r) => r.failed));
    f.dispatchShare = ratio(sum(f3.filter((r) => r.failure_reason.startsWith("Late dispatch")).map((r) => r.failed)), tf);
    f.dispatchBySite = uniq(f3.map((r) => r.site_id)).sort().map((s) => { const x = f3.filter((r) => r.site_id === s); return { s, v: ratio(sum(x.filter((r) => r.failure_reason.startsWith("Late dispatch")).map((r) => r.failed)), sum(x.map((r) => r.failed))) }; });
    f.openUsd = sum(D.backlog.map((r) => r.usd)); f.openN = sum(D.backlog.map((r) => r.n));
    f.old = sum(D.backlog.filter((r) => r.age_band === "30+ days").map((r) => r.n));
    f.noDisp = sum(D.backlog.filter((r) => r.stage.startsWith("Inspected")).map((r) => r.n));
    return f;
  }

  /* ---------- Executive scorecard ---------- */
  function exec() {
    const F = facts();
    const S = D.sc, L3 = S.filter((r) => last3.includes(r.month));
    const w = (k) => ratio(sum(L3.map((r) => r[k] * r.eligible_lines)), sum(L3.map((r) => r.eligible_lines)));
    tiles([
      { k: "Customer OTIF, last 3 months", v: fmt.pct(1)(w("customer_otif")), d: "against the original promise" },
      { k: "Against the latest promise", v: fmt.pct(1)(w("customer_otif_latest_promise")), d: "the flattering version" },
      { k: "Order OTIF, last 3 months", v: fmt.pct(1)(w("order_otif")), d: "every line on the order OTIF" },
      { k: "Supplier OTIF, last 3 months", v: fmt.pct(1)(sum(L3.map((r) => r.supplier_otif)) / L3.length), d: "monthly average" },
      { k: "PPV, 12 months", v: usdK(F.ppvTotal), d: "positive is unfavourable" },
      { k: "Open returns", v: fmt.int(F.openN), d: usdK(F.openUsd) + " expected recoverable" },
    ]);
    const worst = F.region[0];
    const items = [
      ["critical", "Critical", `<b>Meridian Semis' chip shortage cut DC-EU service in Jul to Sep</b>: OTIF on the SKUs built on its chips fell to ${fmt.pct(0)(F.chip)}, against ${fmt.pct(0)(F.nonChip)} for the rest. Short shipments caused ${fmt.pct(0)(F.shortShare)} of DC-EU failures. ${esc(worst.g)} fell from ${fmt.pct(0)(worst.before)} to ${fmt.pct(0)(worst.summer)}. Escalate Meridian (supplier OTIF ${fmt.pct(0)(F.mer.before)} to ${fmt.pct(0)(F.mer.summer)}) and allocate chips by order value.`, "otif.html", "Customer OTIF"],
      ["serious", "Serious", `<b>Refurbish turnaround went from ${F.refBefore.toFixed(0)} to ${F.refSummer.toFixed(0)} days</b> from July, an inspection backlog. ${fmt.int(F.old)} open returns are over 30 days old and ${fmt.int(F.noDisp)} were inspected but never given a disposition. Clear the refurbish queue first: ${usdK(F.openUsd)} is recoverable.`, "returns.html", "Returns"],
      ["serious", "Serious", `<b>DC-US re-promises lines it is about to miss</b> (${fmt.pct(0)(F.us.rep)} of lines since March). Against the latest promise its OTIF is ${fmt.pct(0)(F.us.l)}; against the original it is ${fmt.pct(0)(F.us.o)}. Report the original promise as the headline.`, "otif.html", "Customer OTIF"],
      ["serious", "Serious", `<b>Late dispatch from the warehouse is the most common failure: ${fmt.pct(0)(F.dispatchShare)} of failed lines in the last three months</b> (${F.dispatchBySite.map((r) => `${r.s} ${fmt.pct(0)(r.v)}`).join(", ")}). Lines leave the warehouse too late to make the promise even at standard transit. Review pick-to-dispatch cut-offs at each site.`, "otif.html", "Customer OTIF"],
      ["warning", "Warning", `<b>The CNY move from April added ${usdK(F.cny)} of FX variance</b>, and Kestrel Passives' 9% price rise in May added ${usdK(F.s03)} that standard cost never picked up. Reset Kestrel's standard; hedge or re-quote CNY contracts.`, "ppv.html", "PPV"],
      ["warning", "Warning", `<b>Rapidline's delay in February took DC-AP lines it carried to ${fmt.pct(0)(F.rap)} OTIF</b>, against ${fmt.pct(0)(F.str)} on Straits Logistics. It has recovered; keep the split of volume under review.`, "otif.html", "Customer OTIF"],
    ];
    if (D.dbt) items.push(["good", "Healthy", `<b>${D.dbt.passed} of ${D.dbt.nodes} dbt models and tests pass</b>; the scorecard reconciles to the order-line fact, and a backfill rerun leaves totals unchanged.`, "quality.html", "Data quality"]);
    document.getElementById("insights").innerHTML = items.map(([cls, label, text, href, where]) =>
      `<li><span class="status ${cls}"><i aria-hidden="true">${cls === "good" ? "✓" : "!"}</i>${label}</span><span>${text} <a class="where" href="${href}">${where} →</a></span></li>`).join("");
    card("ex-otif", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.pct(0), yMin: 0.6, yMax: 1, series: [{ name: "Original promise", data: S.map((r) => r.customer_otif), color: 0 }, { name: "Latest promise", data: S.map((r) => r.customer_otif_latest_promise), color: 1, dashed: true }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "eligible_lines", label: "Eligible lines", fmt: fmt.int }, { key: "customer_otif", label: "OTIF", fmt: fmt.pct(1) }, { key: "customer_otif_latest_promise", label: "OTIF, latest promise", fmt: fmt.pct(1) }, { key: "on_time_rate", label: "On time", fmt: fmt.pct(1) }, { key: "in_full_rate", label: "In full", fmt: fmt.pct(1) }, { key: "order_otif", label: "Order OTIF", fmt: fmt.pct(1) }], rows: S });
    card("ex-sup", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.pct(0), yMin: 0.6, yMax: 1, series: [{ name: "Supplier OTIF", data: S.map((r) => r.supplier_otif), color: 0 }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "supplier_otif", label: "Supplier OTIF", fmt: fmt.pct(1) }], rows: S });
    const pm = months.map((m) => D.ppv.filter((r) => r.month === m));
    card("ex-ppv", (el) => bar(el, { x: months, xFmt: mon, yFmt: usdK, stack: true, series: [{ name: "Price effect", data: pm.map((r) => sum(r.map((x) => x.price))), color: 0 }, { name: "FX effect", data: pm.map((r) => sum(r.map((x) => x.fx))), color: 1 }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "ppv_usd", label: "PPV", fmt: usdK }, { key: "ppv_pct", label: "Share of standard spend", fmt: fmt.rel(1) }], rows: S });
    card("ex-ret", (el) => line(el, { x: months, xFmt: mon, yFmt: (v) => Math.round(v) + " d", yMin: 0, series: [{ name: "Median", data: S.map((r) => r.median_return_turnaround_days), color: 0 }, { name: "P90", data: S.map((r) => r.p90_return_turnaround_days), color: 1 }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "returns", label: "Returns", fmt: fmt.int }, { key: "median_return_turnaround_days", label: "Median days", fmt: fmt.num(1) }, { key: "p90_return_turnaround_days", label: "P90 days", fmt: fmt.num(1) }, { key: "recovery_usd", label: "Recovered", fmt: usdK }], rows: S });
  }

  /* ---------- Customer OTIF ---------- */
  function otif() {
    const F = facts();
    const C = D.cust;
    const reg = uniq(C.map((r) => r.region)).sort();
    tiles([
      { k: "Biggest summer drop", v: F.region[0].g, d: `${fmt.pct(0)(F.region[0].before)} to ${fmt.pct(0)(F.region[0].summer)}` },
      { k: "Meridian-chip SKUs at DC-EU", v: fmt.pct(0)(F.chip), d: `Jul to Sep; other SKUs ${fmt.pct(0)(F.nonChip)}` },
      { k: "Short shipments", v: fmt.pct(0)(F.shortShare), d: "of DC-EU failures, Jul to Sep" },
      { k: "DC-US re-promised lines", v: fmt.pct(0)(F.us.rep), d: "since March 2026" },
    ]);
    const cells = [];
    reg.forEach((g, yi) => months.forEach((m, xi) => cells.push([xi, yi, rate(C.filter((r) => r.region === g && r.month === m))])));
    card("ot-region", (el) => heatmap(el, { x: months, y: reg, cells, min: 0.6, max: 0.9, fmt: fmt.pct(0), xLabel: mon, yLabel: (v) => v }),
      { cols: [{ key: "g", label: "Region" }, { key: "before", label: "Nov to May", fmt: fmt.pct(1) }, { key: "summer", label: "Jul to Sep", fmt: fmt.pct(1) }], rows: F.region });
    const fr = D.fail_reason.filter((r) => last3.includes(r.month));
    const reasons = uniq(fr.map((r) => r.failure_reason)).map((x) => ({ x, n: sum(fr.filter((r) => r.failure_reason === x).map((r) => r.failed)) })).sort((a, b) => b.n - a.n);
    card("ot-reason", (el) => bar(el, { horizontal: true, x: reasons.map((r) => r.x), yFmt: fmt.int, series: [{ name: "Failed lines", data: reasons.map((r) => r.n), color: 0, labels: true }] }),
      { cols: [{ key: "x", label: "Reason" }, { key: "n", label: "Failed lines", fmt: fmt.int }], rows: reasons });
    const src = D.by_source.filter((r) => r.site_id === "DC-EU");
    card("ot-source", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.pct(0), yMin: 0, yMax: 1, series: [{ name: "Meridian-chip SKUs", data: byMonth(src, (r) => r.supplier_id === "S07"), color: 0 }, { name: "Other SKUs", data: byMonth(src, (r) => r.supplier_id !== "S07"), color: 1 }] }),
      { cols: [{ key: "m", label: "Month", fmt: mon }, { key: "a", label: "Meridian-chip SKUs", fmt: fmt.pct(1) }, { key: "b", label: "Other SKUs", fmt: fmt.pct(1) }], rows: months.map((m, i) => ({ m, a: byMonth(src, (r) => r.supplier_id === "S07")[i], b: byMonth(src, (r) => r.supplier_id !== "S07")[i] })) });
    const fs = D.fail_sku.slice(0, 25), tot = sum(D.fail_sku.map((r) => r.failed));
    let run = 0; const cum = fs.map((r) => (run += r.failed) / tot);
    card("ot-sku", (el) => {
      const ch = bar(el, { x: fs.map((r) => r.sku), yFmt: fmt.int, series: [{ name: "Failed lines", data: fs.map((r) => r.failed), color: 0 }] });
      return ch;
    }, { cols: [{ key: "sku", label: "SKU" }, { key: "sku_name", label: "Name" }, { key: "family", label: "Family" }, { key: "abc_band", label: "ABC" }, { key: "failed", label: "Failed lines", fmt: fmt.int }, { key: "short", label: "Short shipments", fmt: fmt.int }, { key: "cum", label: "Cumulative share", fmt: fmt.pct(0) }], rows: fs.map((r, i) => Object.assign({ cum: cum[i] }, r)) });
    const sub = document.querySelector("#ot-sku .sub");
    if (sub) sub.textContent = `Top 25 of ${D.fail_sku.length} SKUs, failed eligible lines. These 25 hold ${fmt.pct(0)(cum[cum.length - 1])} of all failures; the top 5 hold ${fmt.pct(0)(cum[4])}`;
    const us = C.filter((r) => r.site_id === "DC-US");
    card("ot-policy", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.pct(0), yMin: 0.6, yMax: 1, series: [{ name: "Original promise", data: byMonth(us, () => true), color: 0 }, { name: "Latest promise", data: byMonth(us, () => true, "otif_latest"), color: 1, dashed: true }] }),
      { cols: [{ key: "m", label: "Month", fmt: mon }, { key: "o", label: "Original", fmt: fmt.pct(1) }, { key: "l", label: "Latest", fmt: fmt.pct(1) }], rows: months.map((m, i) => ({ m, o: byMonth(us, () => true)[i], l: byMonth(us, () => true, "otif_latest")[i] })) });
    const ap = C.filter((r) => r.site_id === "DC-AP");
    card("ot-carrier", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.pct(0), yMin: 0.4, yMax: 1, series: [{ name: "Rapidline", data: byMonth(ap, (r) => r.carrier === "Rapidline"), color: 0 }, { name: "Straits Logistics", data: byMonth(ap, (r) => r.carrier === "Straits Logistics"), color: 1 }] }),
      { cols: [{ key: "m", label: "Month", fmt: mon }, { key: "a", label: "Rapidline", fmt: fmt.pct(1) }, { key: "b", label: "Straits Logistics", fmt: fmt.pct(1) }], rows: months.map((m, i) => ({ m, a: byMonth(ap, (r) => r.carrier === "Rapidline")[i], b: byMonth(ap, (r) => r.carrier === "Straits Logistics")[i] })) });
    table(document.getElementById("drill"), [{ key: "order_line_id", label: "Order line" }, { key: "region", label: "Region" }, { key: "sku_name", label: "SKU" }, { key: "original_promise_date", label: "Promised" }, { key: "eligible_qty", label: "Eligible", fmt: fmt.int }, { key: "delivered_by_original", label: "By promise", fmt: fmt.int }, { key: "delivered_qty", label: "Delivered to date", fmt: fmt.int }, { key: "shipments", label: "Shipments" }, { key: "failure_reason", label: "Reason" }], D.drill);
    document.getElementById("drill").hidden = false;
    const s = document.querySelector("#ot-drill .sub");
    if (s) s.textContent = `DC-EU, Meridian-chip SKUs, last three months: ${fmt.int(D.drill_count)} failed lines, the ${D.drill.length} with the largest shortfall at the promise date`;
  }

  /* ---------- Supplier OTIF ---------- */
  function supplier() {
    const F = facts();
    const S = D.sup, ids = D.suppliers.map((s) => s.supplier_id);
    const cells = [];
    ids.forEach((s, yi) => months.forEach((m, xi) => cells.push([xi, yi, rate(S.filter((r) => r.supplier_id === s && r.month === m))])));
    const win = ids.map((s) => ({ s: SUP[s], before: rate(S.filter((r) => r.supplier_id === s && r.month < "2026-06-01")), summer: rate(S.filter((r) => r.supplier_id === s && SUMMER.includes(r.month))) }));
    tiles([
      { k: "Meridian Semis, Jul to Sep", v: fmt.pct(0)(F.mer.summer), d: `from ${fmt.pct(0)(F.mer.before)} before the shortage` },
      { k: "All suppliers, last 3 months", v: fmt.pct(1)(rate(S.filter((r) => last3.includes(r.month)))), d: "purchase-order lines" },
    ]);
    card("su-heat", (el) => heatmap(el, { x: months, y: ids, cells, min: 0.5, max: 1, fmt: fmt.pct(0), xLabel: mon, yLabel: (v) => SUP[v] }),
      { cols: [{ key: "s", label: "Supplier" }, { key: "before", label: "Nov to May", fmt: fmt.pct(1) }, { key: "summer", label: "Jul to Sep", fmt: fmt.pct(1) }], rows: win });
    card("su-window", (el) => bar(el, { horizontal: true, x: win.map((r) => r.s), yFmt: fmt.pct(0), yMin: 0, yMax: 1, series: [{ name: "Nov to May", data: win.map((r) => r.before), color: 0 }, { name: "Jul to Sep", data: win.map((r) => r.summer), color: 1 }] }),
      { cols: [{ key: "s", label: "Supplier" }, { key: "before", label: "Nov to May", fmt: fmt.pct(1) }, { key: "summer", label: "Jul to Sep", fmt: fmt.pct(1) }], rows: win });
    const q = (s) => months.map((m) => sum(S.filter((r) => r.supplier_id === s && r.month === m).map((r) => r.qty_late)));
    const top = ids.map((s) => ({ s, v: sum(q(s)) })).sort((a, b) => b.v - a.v).slice(0, 3).map((r) => r.s);
    card("su-qty", (el) => line(el, { x: months, xFmt: mon, yFmt: fmt.compact, yMin: 0, series: top.map((s, i) => ({ name: SUP[s], data: q(s), color: i })) }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "supplier_name", label: "Supplier" }, { key: "qty_late", label: "Units late", fmt: fmt.int }, { key: "otif", label: "OTIF lines" }, { key: "n", label: "PO lines" }], rows: S });
    const qq = ids.map((s) => { const r = S.filter((x) => x.supplier_id === s && last3.includes(x.month)); return { s: SUP[s], late: sum(r.map((x) => x.qty_late)), otif: rate(r), lines: sum(r.map((x) => x.n)) }; }).sort((a, b) => b.late - a.late);
    table(document.getElementById("queue"), [{ key: "s", label: "Supplier" }, { key: "lines", label: "PO lines", fmt: fmt.int }, { key: "otif", label: "OTIF", fmt: fmt.pct(1) }, { key: "late", label: "Units late at promise", fmt: fmt.int }], qq);
    document.getElementById("queue").hidden = false;
  }

  /* ---------- Returns ---------- */
  function returns() {
    const F = facts();
    const R = D.ret, disp = uniq(R.map((r) => r.disposition)).filter(Boolean).sort();
    const med = (d) => months.map((m) => { const r = R.find((x) => x.month === m && x.disposition === d); return r ? r.median_days : null; });
    tiles([
      { k: "Refurbish median, Jul to Sep", v: F.refSummer.toFixed(0) + " days", d: `from ${F.refBefore.toFixed(0)} days before July` },
      { k: "Open returns", v: fmt.int(F.openN), d: `${fmt.int(F.old)} over 30 days old` },
      { k: "Inspected, no disposition", v: fmt.int(F.noDisp), d: "stuck after inspection" },
      { k: "Expected recoverable", v: usdK(F.openUsd), d: "open returns, demo recovery rates" },
    ]);
    card("re-tat", (el) => line(el, { x: months, xFmt: mon, yFmt: (v) => Math.round(v) + " d", yMin: 0, endLabels: false, series: disp.map((d, i) => ({ name: d, data: med(d), color: i })) }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "disposition", label: "Disposition" }, { key: "returns", label: "Returns", fmt: fmt.int }, { key: "median_days", label: "Median days", fmt: fmt.num(1) }, { key: "p90_days", label: "P90 days", fmt: fmt.num(1) }], rows: R.filter((r) => r.disposition) });
    card("re-p90", (el) => line(el, { x: months, xFmt: mon, yFmt: (v) => Math.round(v) + " d", yMin: 0, series: [{ name: "P90", data: D.sc.map((r) => r.p90_return_turnaround_days), color: 0 }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "p90_return_turnaround_days", label: "P90 days", fmt: fmt.num(1) }], rows: D.sc });
    const bands = ["0-6 days", "7-13 days", "14-29 days", "30+ days"], stages = ["Awaiting inspection", "Inspected, no disposition"];
    card("re-backlog", (el) => bar(el, { x: bands, yFmt: fmt.int, stack: true, series: stages.map((s, i) => ({ name: s, data: bands.map((b) => sum(D.backlog.filter((r) => r.stage === s && r.age_band === b).map((r) => r.n))), color: i })) }),
      { cols: [{ key: "stage", label: "Stage" }, { key: "age_band", label: "Age" }, { key: "n", label: "Returns", fmt: fmt.int }, { key: "usd", label: "Recoverable", fmt: usdK }], rows: D.backlog });
    const v = disp.map((d) => { const r = R.filter((x) => x.disposition === d); return { d, rec: sum(r.map((x) => x.recovery)), cost: sum(r.map((x) => x.handling)), n: sum(r.map((x) => x.returns)) }; });
    card("re-value", (el) => bar(el, { x: v.map((r) => r.d), yFmt: usdK, series: [{ name: "Recovered", data: v.map((r) => r.rec), color: 0 }, { name: "Handling cost", data: v.map((r) => r.cost), color: 1 }] }),
      { cols: [{ key: "d", label: "Disposition" }, { key: "n", label: "Returns", fmt: fmt.int }, { key: "rec", label: "Recovered", fmt: usdK }, { key: "cost", label: "Handling cost", fmt: usdK }, { key: "per", label: "Cost per return", fmt: fmt.usd(2) }], rows: v.map((r) => Object.assign({ per: r.cost / r.n }, r)) });
    const fams = uniq(D.backlog_family.map((r) => r.family));
    card("re-family", (el) => bar(el, { horizontal: true, stack: true, x: fams, yFmt: usdK, series: stages.map((s, i) => ({ name: s, data: fams.map((f) => sum(D.backlog_family.filter((r) => r.family === f && r.stage === s).map((r) => r.usd))), color: i })) }),
      { cols: [{ key: "family", label: "Family" }, { key: "stage", label: "Stage" }, { key: "n", label: "Returns", fmt: fmt.int }, { key: "usd", label: "Recoverable", fmt: usdK }], rows: D.backlog_family });
  }

  /* ---------- PPV ---------- */
  function ppv() {
    const F = facts();
    const P = D.ppv, ids = D.suppliers.map((s) => s.supplier_id);
    tiles([
      { k: "PPV, 12 months", v: usdK(F.ppvTotal), d: "positive is unfavourable" },
      { k: "CNY FX effect since April", v: usdK(F.cny), d: "CNY rose about 5% against standard" },
      { k: "Kestrel price effect since May", v: usdK(F.s03), d: "9% rise, standard unchanged" },
      { k: "JPY FX effect", v: usdK(F.jpy), d: "favourable: yen below standard" },
    ]);
    const pm = months.map((m) => P.filter((r) => r.month === m));
    card("pv-month", (el) => bar(el, { x: months, xFmt: mon, yFmt: usdK, stack: true, series: [{ name: "Price effect", data: pm.map((r) => sum(r.map((x) => x.price))), color: 0 }, { name: "FX effect", data: pm.map((r) => sum(r.map((x) => x.fx))), color: 1 }] }),
      { cols: [{ key: "month", label: "Month", fmt: mon }, { key: "supplier_id", label: "Supplier", fmt: (s) => SUP[s] }, { key: "currency", label: "Currency" }, { key: "std", label: "Standard spend", fmt: usdK }, { key: "price", label: "Price effect", fmt: usdK }, { key: "fx", label: "FX effect", fmt: usdK }, { key: "ppv", label: "PPV", fmt: usdK }], rows: P });
    const bs = ids.map((s) => { const r = P.filter((x) => x.supplier_id === s); return { s: SUP[s], price: sum(r.map((x) => x.price)), fx: sum(r.map((x) => x.fx)), ppv: sum(r.map((x) => x.ppv)), cur: (D.suppliers.find((x) => x.supplier_id === s) || {}).currency }; }).sort((a, b) => b.ppv - a.ppv);
    card("pv-sup", (el) => bar(el, { horizontal: true, x: bs.map((r) => r.s), yFmt: usdK, series: [{ name: "Price effect", data: bs.map((r) => r.price), color: 0 }, { name: "FX effect", data: bs.map((r) => r.fx), color: 1 }] }),
      { cols: [{ key: "s", label: "Supplier" }, { key: "cur", label: "Currency" }, { key: "price", label: "Price effect", fmt: usdK }, { key: "fx", label: "FX effect", fmt: usdK }, { key: "ppv", label: "PPV", fmt: usdK }], rows: bs });
    const l6 = months.slice(-6);
    const pct = ids.map((s) => { const r = P.filter((x) => x.supplier_id === s && l6.includes(x.month)); return { s: SUP[s], v: ratio(sum(r.map((x) => x.ppv)), sum(r.map((x) => x.std))) }; }).sort((a, b) => b.v - a.v);
    card("pv-pct", (el) => bar(el, { horizontal: true, x: pct.map((r) => r.s), yFmt: fmt.rel(1), series: [{ name: "PPV / standard spend", data: pct.map((r) => r.v), color: 0, labels: true }] }),
      { cols: [{ key: "s", label: "Supplier" }, { key: "v", label: "PPV / standard spend", fmt: fmt.rel(2) }], rows: pct });
  }

  /* ---------- Data quality ---------- */
  function quality() {
    tiles([
      { k: "dbt models and tests", v: D.dbt ? `${D.dbt.passed} / ${D.dbt.nodes}` : "–", d: "passing on this build" },
      { k: "Extract date", v: D.as_of, d: "latest event ingested" },
      { k: "Records quarantined", v: fmt.int(sum(D.dq.filter((r) => r.action === "quarantined").map((r) => r.records))), d: "kept out of every KPI, with a reason" },
    ]);
    document.getElementById("checks").innerHTML = `<ul class="insights">${D.dq.map((r) => {
      const cls = r.action === "quarantined" || r.action.startsWith("flagged") ? "warning" : "good";
      const label = r.action === "quarantined" ? "Quarantined" : r.action.startsWith("flagged") ? "Flagged" : "Handled";
      return `<li><span class="status ${cls}"><i aria-hidden="true">${cls === "good" ? "✓" : "!"}</i>${label}</span><span><b>${esc(r.check_name)}:</b> ${fmt.int(r.records)} records in <code>${esc(r.source)}</code>, ${esc(r.action)}.</span></li>`;
    }).join("")}</ul>`;
    const rules = [
      ["Retried events are kept once, at first arrival", "stg_order_events (row_number over event_id)"],
      ["Deliveries are dated in the shipping site's local calendar", "macro local_date; test assert_local_date_used_for_deliveries"],
      ["Split shipments count cumulatively up to the promise date", "fct_order_line; pytest test_split_deliveries_are_cumulative"],
      ["On time, in full and OTIF share one eligible denominator", "rpt_customer_otif_monthly; pytest test_rates_share_one_denominator"],
      ["Order OTIF needs every eligible line OTIF", "fct_order; pytest test_order_otif_uses_every_eligible_line"],
      ["Scorecard reconciles to the line fact, month by month", "assert_otif_reconciles_to_lines; test_scorecard_matches_line_fact"],
      ["Backfill then incremental equals a full build", "int_deliveries (incremental, lookback); make rerun; test_backfill_rerun_matches_full_build"],
      ["Price effect + FX effect = PPV on every invoice line", "assert_ppv_bridge_sums"],
      ["C100 invoices are converted to each before pricing", "stg_invoices.units_per_uom; test_c100_invoices_are_priced_per_each"],
      ["Credit notes are excluded from PPV and counted", "fct_ppv.is_credit_note"],
    ];
    document.getElementById("rules").innerHTML = `<ul class="insights">${rules.map(([r, w]) => `<li><span class="status good"><i aria-hidden="true">✓</i>Tested</span><span><b>${esc(r)}.</b> <code>${esc(w)}</code></span></li>`).join("")}</ul>`;
  }

  const PAGES = { exec, otif, supplier, returns, ppv, quality };
  document.addEventListener("DOMContentLoaded", () => {
    const run = PAGES[document.body.dataset.page];
    if (!window.echarts) { document.querySelector("main").insertAdjacentHTML("afterbegin", '<p class="callout critical">Charts could not load (no network to the chart library). Tables still work.</p>'); }
    run();
  });
})();
