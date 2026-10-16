"""pipeline.load() against the real Postgres image, with an in-memory raw zone."""
import sys

import psycopg2
import pytest

from db_helpers import container_ip, docker, migrate, start_db, wait_ready
from helpers import ROOT

sys.path.insert(0, str(ROOT / "src" / "dsv-pipeline" / "tests"))
sys.path.insert(0, str(ROOT / "src" / "dsv-pipeline"))

from fakes import FakeStore, historical_csv, historical_row, recent_csv, recent_row  # noqa: E402
import pipeline  # noqa: E402
from data import DataError  # noqa: E402

MIGRATOR_PW = "migrator-pw"
HIST = "historical/20260601T113002Z/"
OLD = "recent/20261009T113005Z/Dinesafe.csv"
NEW = "recent/20261012T113012Z/Dinesafe.csv"


@pytest.fixture(scope="module")
def db():
    name = start_db({"DSV_DB_APP_PASSWORD": "app-pw", "DSV_DB_MIGRATOR_PASSWORD": MIGRATOR_PW})
    try:
        assert wait_ready(name), docker("logs", name).stderr
        assert migrate(name).returncode == 0
        yield name
    finally:
        docker("rm", "-f", name, check=False)


@pytest.fixture
def conn(db):
    c = psycopg2.connect(host=container_ip(db), dbname="dinesafe",
                         user="dinesafe_migrator", password=MIGRATOR_PW)
    with c.cursor() as cur:
        cur.execute("DELETE FROM inspections")
        cur.execute("DELETE FROM load_log")
    c.commit()
    yield c
    c.close()


def csv_bytes(writer, rows, tmp_path, name):
    path = tmp_path / name
    writer(path, rows)
    return path.read_bytes()


@pytest.fixture
def store(tmp_path):
    s = FakeStore()
    s.put(HIST + "dinesafe_hist_2022.csv",
          csv_bytes(historical_csv, [historical_row("9", "2022-03-01")], tmp_path, "h22.csv"))
    s.put(HIST + "dinesafe_hist_2023.csv",
          csv_bytes(historical_csv, [historical_row("8", "2023-04-30"),
                                     historical_row("7", "2023-05-01")], tmp_path, "h23.csv"))
    s.put(HIST + "_SUCCESS", b"")
    s.put(OLD, csv_bytes(recent_csv, [recent_row("1", "2023-05-01")], tmp_path, "old.csv"),
          source_last_modified="2026-10-09T08:00:00")
    return s


def count(conn, sql):
    with conn.cursor() as cur:
        cur.execute(sql)
        return cur.fetchone()[0]


def add_new(store, tmp_path, rows):
    store.put(NEW, csv_bytes(recent_csv, rows, tmp_path, "new.csv"),
              source_last_modified="2026-10-12T09:14:00")


def test_empty_table_seeds_and_logs(conn, store):
    assert pipeline.load(store, conn) == "seed"
    assert count(conn, "SELECT count(*) FROM inspections") == 3  # 2 historical + 1 recent
    assert count(conn, "SELECT kind || ' ' || recent_path || ' ' || historical_path FROM load_log") \
        == f"seed {OLD} {HIST}"


def test_second_load_is_already_current(conn, store, capsys):
    pipeline.load(store, conn)
    assert pipeline.load(store, conn) == "skip"
    assert "Already current" in capsys.readouterr().out
    assert count(conn, "SELECT count(*) FROM load_log") == 1


def test_new_recent_file_refreshes_the_window(conn, store, tmp_path):
    pipeline.load(store, conn)
    add_new(store, tmp_path, [recent_row("1", "2023-05-01"), recent_row("2", "2024-01-02")])
    assert pipeline.load(store, conn) == "refresh"
    assert count(conn, "SELECT count(*) FROM inspections") == 4
    assert count(conn, "SELECT rows_deleted || '/' || rows_inserted FROM load_log ORDER BY id DESC LIMIT 1") \
        == "1/2"


def test_new_historical_folder_reseeds(conn, store, tmp_path):
    pipeline.load(store, conn)
    hist2 = "historical/20261014T153259Z/"
    store.put(hist2 + "dinesafe_hist_2022.csv",
              csv_bytes(historical_csv, [historical_row("9", "2022-03-01"),
                                         historical_row("6", "2022-07-01")], tmp_path, "h22b.csv"))
    store.put(hist2 + "_SUCCESS", b"")
    assert pipeline.load(store, conn) == "seed"
    assert count(conn, "SELECT count(*) FROM inspections") == 3  # 2 from the new folder + 1 recent
    assert count(conn, "SELECT rows_deleted || ' ' || historical_path FROM load_log ORDER BY id DESC LIMIT 1") \
        == f"3 {hist2}"
    assert pipeline.load(store, conn) == "skip"


def test_force_reloads_the_current_file(conn, store):
    pipeline.load(store, conn)
    assert pipeline.load(store, conn, force=True) == "refresh"
    assert count(conn, "SELECT count(*) FROM load_log") == 2


# Review focus 3: COPY fails after the DELETE has run.
def test_failed_load_keeps_old_data_and_logs_nothing(conn, store, tmp_path):
    pipeline.load(store, conn)
    add_new(store, tmp_path, [recent_row("1", "2023-05-01", latitude="not-a-number")])
    with pytest.raises(psycopg2.Error):
        pipeline.load(store, conn)
    conn.rollback()
    assert count(conn, "SELECT count(*) FROM inspections") == 3
    assert count(conn, "SELECT count(*) FROM load_log") == 1


def test_empty_raw_zone_is_an_error(conn):
    with pytest.raises(DataError, match="recent/ is empty"):
        pipeline.load(FakeStore(), conn)


def test_seed_without_complete_historical_is_an_error(conn, store):
    del store.blobs[HIST + "_SUCCESS"]
    with pytest.raises(DataError, match="historical/"):
        pipeline.load(store, conn)
    conn.rollback()
    assert count(conn, "SELECT count(*) FROM inspections") == 0


# Final review: a deploy's load overlapping the timer's load must not both
# seed or both refresh. The second waits, then finds the data current.
def test_concurrent_loads_wait_for_each_other(db, conn, store):
    import threading

    other = psycopg2.connect(host=container_ip(db), dbname="dinesafe",
                             user="dinesafe_migrator", password=MIGRATOR_PW)
    try:
        with other.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (pipeline.LOAD_LOCK,))
        result = {}
        worker = threading.Thread(target=lambda: result.setdefault("action", pipeline.load(store, conn)))
        worker.start()
        worker.join(timeout=1)
        assert worker.is_alive(), "load didn't wait for the lock"
        with other.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", (pipeline.LOAD_LOCK,))
        worker.join(timeout=30)
        assert result["action"] == "seed"
    finally:
        other.close()
    assert pipeline.load(store, conn) == "skip"
    assert count(conn, "SELECT count(*) FROM inspections") == 3


# COPY's text format treats a backslash as an escape: "\n" would load as a
# newline, "\N" as NULL, and a trailing "\" would swallow the next tab.
@pytest.mark.parametrize("value", [r"C:\new\table", r"A \N B", "ends in \\", "\\\\"])
def test_backslashes_load_unchanged(conn, value):
    import loader

    row = {col: None for col in loader.INSPECTIONS_COLUMNS} | {
        "establishment_name": value, "establishment_type": "after",
    }
    assert loader.bulk_insert(conn, [row]) == 1
    with conn.cursor() as cur:
        cur.execute("SELECT establishment_name, establishment_type FROM inspections")
        assert cur.fetchall() == [(value, "after")]
    conn.rollback()
