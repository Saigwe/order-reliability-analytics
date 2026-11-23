# Decision memo: where to act first

*Demo results on synthetic data. Figures from [results.md](results.md).*

**Question.** Customer OTIF dipped in the summer. Where did it come from, who owns it, and is it the biggest loss we
should be working on?

**What the analysis supports**

- The dip is one distribution centre and one supplier. DC-EU OTIF on SKUs built on Meridian Semis chips fell to 35.4%
  in July to September, against 83.6% for its other SKUs; Meridian's own OTIF fell from 86.6% to 61.5% in the same
  months. The failed lines are split deliveries that arrived short at the promise date. **Owner: procurement.**
- DC-US reports 97.2% OTIF against the latest promise and 83.0% against the original. The difference is re-promising
  lines it is about to miss. **Owner: DC-US operations; decision: report the original promise.**
- Across all sites, late dispatch from the warehouse is the most common failure (59.5% of failed lines in the last
  three months). This is the steady-state problem; the chip shortage is the acute one. **Owner: warehouse operations.**
- Purchase price variance is $984k unfavourable, and $1.14M of it is the CNY move since April. Kestrel Passives' price
  rise adds $78k because its standard cost was never updated. **Owner: finance and procurement.**
- The refurbish inspection backlog took turnaround from 5 to 36 days; 210 returns are open with about $36k of
  recoverable value. **Owner: returns centre.**

**Recommendation.** (1) Escalate Meridian Semis and allocate chips by order value until supply recovers. (2) Make the
original promise the reported OTIF. (3) Review pick-to-dispatch cut-offs at each site. (4) Re-quote or hedge CNY
contracts and reset Kestrel's standard cost before the next budget. (5) Clear the refurbish queue with temporary
inspection capacity: it is cheap and the value is small, so it should not displace (1) to (4).

**Where uncertainty remains.** Failure reasons follow a fixed rule order, so a line that was both dispatched late and
shipped short counts once. Recovery rates and handling costs are assumptions. The FX effect depends on the standard
rates chosen for the year.
