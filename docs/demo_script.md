# Two-minute walkthrough

1. **Executive scorecard.** Customer OTIF 81.6%, but order OTIF only 66.4%: customers with multi-line orders feel it
   more. The latest-promise figure (86.5%) is the flattering version. The decision list is ranked by severity.
2. **Customer OTIF, region heatmap.** The three European regions turn lighter in July to September; North America and
   APAC do not. It is one distribution centre, DC-EU.
3. **Why lines failed.** Late dispatch is the biggest reason overall, but in DC-EU this summer short shipments jump.
4. **DC-EU: Meridian-chip SKUs against the rest.** The SKUs built on Meridian Semis chips fall to 35%; the rest hold at
   84%. The Pareto shows the same SKUs at the top.
5. **The lines behind it.** The drill table lists the failed lines: eligible quantity, quantity delivered by the promise
   date, two shipments each. The split delivery arrived after the promise.
6. **Supplier OTIF.** Meridian Semis drops from 87% to 62% in the same months and tops the escalation queue. The
   customer breach and the supplier breach agree.
7. **Decision.** Escalate Meridian and allocate scarce chips by order value; report OTIF against the original promise
   so DC-US re-promising stops hiding misses.
8. **Returns and PPV.** The refurbish backlog holds about $36k of recoverable value; the CNY move cost $1.14M. Clear the
   backlog because it is cheap, but put finance time on currency.
9. **Data quality.** 4,517 retried events and 16,254 double scans dropped, 40 records quarantined, every test passing,
   and a backfill rerun leaves totals unchanged.
