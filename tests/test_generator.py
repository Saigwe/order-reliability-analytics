"""The generator writes every table the warehouse reads."""
import yaml

from conftest import ROOT


def test_every_source_was_written():
    src = yaml.safe_load((ROOT / "dbt" / "models" / "staging" / "_sources.yml").read_text(encoding="utf-8"))
    names = [t["name"] for t in src["sources"][0]["tables"]]
    missing = [n for n in names if not (ROOT / "data" / "raw" / f"{n}.parquet").exists()]
    assert not missing, missing
