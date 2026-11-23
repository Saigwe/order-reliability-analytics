import os
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get("ORDERS_DB", ROOT / "warehouse" / "orders.duckdb"))


@pytest.fixture(scope="session")
def con():
    if not DB.exists():
        pytest.skip(f"{DB} not built: run `make data dbt` first")
    with duckdb.connect(str(DB), read_only=True) as c:
        yield c


def one(con, sql):
    return con.execute(sql).fetchone()
