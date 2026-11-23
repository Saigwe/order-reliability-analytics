"""Overview and detail agree: the executive scorecard, monthly marts and line fact all add up to the same eligible base."""
from conftest import one


def test_scorecard_matches_line_fact(con):
    (gap,) = one(con, """select max(abs(s.customer_otif - f.otif)) from gold.rpt_exec_scorecard s
                         join (select promise_month, avg(is_otif_original::int) otif from gold.fct_order_line where is_eligible group by 1) f
                           on f.promise_month = s.month""")
    assert gap < 1e-9


def test_order_otif_uses_every_eligible_line(con):
    bad = one(con, """select count(*) from gold.fct_order o
                      join (select order_id, bool_and(is_otif_original) all_ok from gold.fct_order_line where is_eligible group by 1) l using (order_id)
                      where o.is_otif_original <> l.all_ok""")[0]
    assert bad == 0
    o, l = one(con, "select avg(order_otif), avg(customer_otif) from gold.rpt_exec_scorecard")
    assert o < l


def test_rates_share_one_denominator(con):
    rows = con.execute("""select sum(eligible_lines), sum(on_time_lines), sum(in_full_lines), sum(otif_lines_original)
                          from gold.rpt_customer_otif_monthly""").fetchone()
    n, ot, inf, otif = rows
    assert otif <= min(ot, inf) <= n


def test_backfill_rerun_matches_full_build(con):
    # `make rerun` builds int_deliveries from a cut-off and then incrementally; it must equal the deduplicated log.
    a, b = one(con, """select (select count(*) from silver.int_deliveries),
                              (select count(*) from silver.stg_order_events where event_type = 'shipment_delivered' and has_order_line)""")
    assert a == b


def test_split_deliveries_are_cumulative(con):
    (n,) = one(con, """select count(*) from gold.fct_order_line where shipments > 1 and is_otif_original
                       and delivered_by_original < eligible_qty""")
    assert n == 0
    (split,) = one(con, "select count(*) from gold.fct_order_line where shipments > 1")
    assert split > 100


def test_cancellations_reduce_the_eligible_quantity(con):
    (n,) = one(con, "select count(*) from gold.fct_order_line where cancelled_qty > 0 and eligible_qty <> ordered_qty - least(cancelled_qty, ordered_qty)")
    assert n == 0
