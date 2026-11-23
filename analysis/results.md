# Results from the current build

Written by `analysis/report.py` from the gold marts on every `make dashboards`. Demo results on synthetic data.

| Measure | Value | Note |
|---|---|---|
| Customer OTIF, 12 months, original promise | 81.6% | 105,107 eligible order lines |
| Customer OTIF against the latest promise | 86.5% | what re-promising would report |
| Order OTIF (every line OTIF) | 66.4% | monthly average |
| DC-EU, Meridian-chip SKUs, Jul to Sep | 35.4% | other SKUs 83.6% |
| Meridian Semis supplier OTIF | 86.6% to 61.5% | Nov to May, then Jul to Sep |
| DC-US OTIF since March, original against latest promise | 83.0% against 97.2% | re-promising hides misses |
| Late warehouse dispatch, share of failed lines | 59.5% | last three months |
| Rapidline OTIF, February 2026 | 49.5% | carrier delay |
| Purchase price variance, 12 months | $984k | positive is unfavourable |
| CNY FX effect since April | $1.14M | CNY about 5% above standard |
| Kestrel Passives price effect since May | $78k | 9% rise, standard cost unchanged |
| Refurbish median turnaround | 5 to 36 days | before July, then Jul to Sep |
| Open returns at extract | 210 | 86 over 30 days; $36k recoverable |
| Retried events dropped | 4,517 | kept once, at first arrival |
| Warehouse double scans dropped | 16,254 |  |
| Records quarantined | 40 | zero quantity, unknown order line |
