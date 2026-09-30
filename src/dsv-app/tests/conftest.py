import sys
import os
from datetime import date, datetime
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    return app_module.app.test_client()


@pytest.fixture(autouse=True)
def seeded_stats_cache():
    """Fill the stats cache with a 2001-01-01..today range so nav rendering never hits a real DB."""
    app_module._stats_cache["data"] = {
        "total_inspections": 1, "years_of_data": 1,
        "min_date": date(2001, 1, 1), "max_date": date.today(),
    }
    app_module._stats_cache["fetched_at"] = datetime.now()
