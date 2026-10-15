import pytest

import fakes  # noqa: F401  (puts src/dsv-pipeline on sys.path)
import pipeline
from data import DataError


R1, R2 = "recent/a/Dinesafe.csv", "recent/b/Dinesafe.csv"
H1, H2 = "historical/a/", "historical/b/"


# loaded: (recent path of the last load, historical path of the last seed).
# newest: (newest recent file, newest complete historical folder) in Blob.
@pytest.mark.parametrize("empty,loaded,newest,force,expected", [
    (True, (None, None), (R2, H1), False, "seed"),
    (True, (R2, H1), (R2, H1), False, "seed"),
    (False, (R2, H1), (R2, H1), False, "skip"),
    (False, (R1, H1), (R2, H1), False, "refresh"),
    (False, (R2, H1), (R2, H1), True, "refresh"),
    # A new historical folder reseeds, even when the recent file is current.
    (False, (R2, H1), (R2, H2), False, "seed"),
    (False, (R1, H1), (R2, H2), True, "seed"),
    (False, (R2, None), (R2, H1), False, "seed"),
    # No historical folder in Blob: nothing to reseed from.
    (False, (R1, H1), (R2, None), False, "refresh"),
])
def test_decide(empty, loaded, newest, force, expected):
    assert pipeline.decide(empty, loaded, newest, force) == expected


class Recorder:
    def __init__(self, monkeypatch, fail=None):
        self.calls = []
        self.fail = fail
        for name in ("ingest", "check_fresh"):
            monkeypatch.setattr(pipeline.data, name, self.make(name))
        monkeypatch.setattr(pipeline, "load", self.make("load"))

    def make(self, name):
        def fn(*args, **kwargs):
            self.calls.append((name, kwargs))
            if name == self.fail:
                raise DataError(f"{name} broke")
        return fn


class FakeConn:
    closed = False

    def close(self):
        self.closed = True


def run_main(argv, **kwargs):
    conn = FakeConn()
    code = pipeline.main(argv, store_factory=lambda: "store", connect=lambda: conn, **kwargs)
    return code, conn


def test_run_ingests_loads_then_checks_freshness(monkeypatch):
    rec = Recorder(monkeypatch)
    code, conn = run_main(["run", "--force"])
    assert code == 0
    assert [c[0] for c in rec.calls] == ["ingest", "load", "check_fresh"]
    assert rec.calls[0][1] == {"force": True, "historical": False}
    assert rec.calls[1][1] == {"force": False}  # --force applies to ingest only
    assert conn.closed


def test_load_passes_force_and_never_ingests(monkeypatch):
    rec = Recorder(monkeypatch)
    assert run_main(["load", "--force"])[0] == 0
    assert rec.calls == [("load", {"force": True})]


def test_ingest_does_not_connect_to_the_database(monkeypatch):
    rec = Recorder(monkeypatch)

    def no_db():
        raise AssertionError("connected")

    assert pipeline.main(["ingest", "--historical"], store_factory=lambda: "s", connect=no_db) == 0
    assert rec.calls == [("ingest", {"force": False, "historical": True})]


def test_failed_ingest_stops_the_run(monkeypatch, capsys):
    rec = Recorder(monkeypatch, fail="ingest")
    assert run_main(["run"])[0] == 1
    assert [c[0] for c in rec.calls] == ["ingest"]
    assert "pipeline: ingest broke" in capsys.readouterr().err


def test_stale_data_fails_the_run(monkeypatch):
    Recorder(monkeypatch, fail="check_fresh")
    assert run_main(["run"])[0] == 1


def test_load_rejects_historical(capsys):
    with pytest.raises(SystemExit) as exc:
        pipeline.main(["load", "--historical"])
    assert exc.value.code == 2


def test_missing_account_is_a_clear_error(tmp_path, monkeypatch, capsys):
    token = tmp_path / "token"
    token.write_text("t")
    monkeypatch.delenv("DSV_STORAGE_ACCOUNT", raising=False)
    monkeypatch.setenv("DSV_TOKEN_FILE", str(token))
    assert pipeline.main(["load"]) == 1
    assert "DSV_STORAGE_ACCOUNT" in capsys.readouterr().err


def test_missing_token_file_is_a_clear_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("DSV_STORAGE_ACCOUNT", "stdsvstg01")
    monkeypatch.setenv("DSV_TOKEN_FILE", str(tmp_path / "nope"))
    assert pipeline.main(["load"]) == 1
    assert "token" in capsys.readouterr().err
