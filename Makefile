PY ?= python
DB ?= warehouse/orders.duckdb
CUTOFF ?= 2026-10-01

.PHONY: all ci data dbt rerun test dashboards serve clean

all: data dbt dashboards                                  ## everything, about a minute
ci: data dbt rerun test                                   ## what GitHub Actions runs

data:
	$(PY) generator/simulate.py --out data/raw

dbt:
	mkdir -p warehouse
	cd dbt && DUCKDB_PATH=../$(DB) dbt build --profiles-dir .

# Backfill proof: build from events ingested up to CUTOFF, then let the incremental model pick up the rest
# (late and retried events included) and run every test again. Totals must match a full build.
rerun:
	cd dbt && DUCKDB_PATH=../$(DB) dbt build --profiles-dir . --full-refresh --vars '{ingest_cutoff: "$(CUTOFF)"}'
	cd dbt && DUCKDB_PATH=../$(DB) dbt build --profiles-dir .

test:
	ORDERS_DB=$(DB) $(PY) -m pytest -q

dashboards:
	$(PY) dashboards/export.py --db $(DB) --out dashboards/site/data.json
	$(PY) dashboards/build.py
	$(PY) analysis/report.py --db $(DB) --out analysis/results.md

serve:
	$(PY) -m http.server 8000 --directory dashboards/site

clean:
	rm -rf warehouse data/raw dbt/target dbt/logs dashboards/site/data.json dashboards/site/data.js dashboards/site/*.html
