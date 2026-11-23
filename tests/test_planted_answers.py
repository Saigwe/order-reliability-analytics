"""Every planted problem in generator/simulate.py must come back out of the gold marts, found by the reports' own logic."""
import json

from conftest import ROOT, one

KEY = json.loads((ROOT / "data" / "raw" / "answer_key.json").read_text(encoding="utf-8"))
WINDOW = "promise_month between '2026-07-01' and '2026-09-01'"


def test_chip_shortage_shows_as_short_shipments_at_dc_eu(con):
    chips = "', '".join(KEY["shortage"]["skus"])
    hit, rest = one(con, f"""select avg(case when sku in ('{chips}') then is_otif_original::int end),
                                    avg(case when sku not in ('{chips}') then is_otif_original::int end)
                             from gold.fct_order_line where is_eligible and site_id = 'DC-EU' and {WINDOW}""")
    assert hit < 0.5 and rest > 0.75
    (reason,) = one(con, f"""select failure_reason from gold.rpt_otif_failures where site_id = 'DC-EU' and {WINDOW}
                             and sku in ('{chips}') group by 1 order by sum(failed_lines) desc limit 1""")
    assert reason == "Short shipment (stock)"


def test_chip_shortage_reaches_every_region_served_by_dc_eu(con):
    rows = dict(con.execute(f"""select region, sum(otif_lines_original)::double / sum(eligible_lines) - 0 from gold.rpt_customer_otif_monthly
                                where {WINDOW} group by 1""").fetchall())
    for region in KEY["shortage"]["regions_hit"]:
        assert rows[region] < rows["North America"] - 0.05, region


def test_supplier_scorecard_finds_the_same_supplier(con):
    rows = con.execute(f"""select supplier_id, sum(otif_lines)::double / sum(po_lines) from gold.rpt_supplier_otif_monthly
                           where {WINDOW} group by 1 order by 2""").fetchall()
    assert rows[0][0] == KEY["shortage"]["supplier"] and rows[0][1] < rows[1][1] - 0.1


def test_repromising_flatters_dc_us_only_after_it_started(con):
    def gap(where):
        o, l = one(con, f"""select sum(otif_lines_original)::double / sum(eligible_lines), sum(otif_lines_latest)::double / sum(eligible_lines)
                            from gold.rpt_customer_otif_monthly where site_id = 'DC-US' and {where}""")
        return l - o
    assert gap(f"promise_month < '{KEY['repromise']['from']}'") < 0.03
    assert gap(f"promise_month >= '{KEY['repromise']['from']}'") > 0.10


def test_carrier_delay_is_visible_and_attributed(con):
    rap, other = one(con, """select sum(otif_lines_original) filter (where carrier = 'Rapidline')::double / sum(eligible_lines) filter (where carrier = 'Rapidline'),
                                    sum(otif_lines_original) filter (where carrier <> 'Rapidline')::double / sum(eligible_lines) filter (where carrier <> 'Rapidline')
                             from gold.rpt_customer_otif_monthly where site_id = 'DC-AP' and promise_month = '2026-02-01'""")
    assert rap < other - 0.2
    (n,) = one(con, """select count(*) from gold.fct_order_line where carrier = 'Rapidline' and failure_reason = 'Carrier transit delay'
                       and original_promise_date between '2026-01-26' and '2026-03-08'""")
    assert n > 100


def test_price_rise_is_a_price_effect_and_cny_move_is_an_fx_effect(con):
    s = KEY["price_rise"]["supplier"]
    before, after = one(con, f"""select sum(price_effect_usd) filter (where receipt_month < '{KEY['price_rise']['from']}'),
                                        sum(price_effect_usd) filter (where receipt_month >= '{KEY['price_rise']['from']}')
                                 from gold.rpt_ppv_monthly where supplier_id = '{s}'""")
    assert after > 50_000 and abs(before) < after / 5
    fx_before, fx_after = one(con, f"""select sum(fx_effect_usd) filter (where receipt_month < '{KEY['fx_move']['from']}'),
                                              sum(fx_effect_usd) filter (where receipt_month >= '{KEY['fx_move']['from']}')
                                       from gold.rpt_ppv_monthly where currency = '{KEY['fx_move']['currency']}'""")
    assert fx_after > 300_000 and fx_after > 5 * abs(fx_before)


def test_ppv_bridge_reconciles_to_invoice_lines(con):
    a, b, c = one(con, "select sum(ppv_usd), sum(price_effect_usd) + sum(fx_effect_usd), (select sum(ppv_usd) from gold.fct_ppv) from gold.rpt_ppv_monthly")
    assert abs(a - b) < 1 and abs(a - c) < 1


def test_c100_invoices_are_priced_per_each(con):
    (ratio,) = one(con, "select avg(actual_unit_usd / standard_unit_cost_usd) from gold.fct_ppv where uom = 'C100' and receipt_month < '2026-05-01'")
    assert 0.95 < ratio < 1.05


def test_inspection_backlog_shows_in_refurbish_turnaround(con):
    before, during = one(con, """select median(turnaround_days) filter (where received_month < '2026-07-01'),
                                        median(turnaround_days) filter (where received_month between '2026-07-01' and '2026-09-01')
                                 from gold.fct_return where disposition = 'Refurbish'""")
    assert during > 4 * before
    (other,) = one(con, """select median(turnaround_days) from gold.fct_return where disposition <> 'Refurbish'
                           and received_month between '2026-07-01' and '2026-09-01'""")
    assert other < 10


def test_bad_records_are_caught_and_counted(con):
    dq = dict(con.execute("select check_name, records from gold.rpt_data_quality").fetchall())
    assert dq["Order lines with zero quantity"] == KEY["bad_records"]["zero_qty_lines"]
    assert dq["Deliveries for unknown order lines"] == KEY["bad_records"]["orphan_deliveries"]
    assert dq["Order events: duplicate retries dropped"] > 1000
    assert dq["Warehouse double scans"] > 1000
