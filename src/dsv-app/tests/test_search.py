from datetime import date
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import search_conn

HINT = "Search by restaurant name or address, like pizza or queen."


def _result(n=1, name="Pizza Pizza", status="Pass", est_type="Restaurant", unit=None):
    """One row as returned by the search query's RealDictCursor."""
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": name,
        "street": "123 Queen St W",
        "unit": unit,
        "establishment_status": status,
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 14,
        "first_inspected": date(2019, 3, 4),
        "establishment_type": est_type,
    }


def _search(client, q, rows=()):
    """GET /search?q=... with a fake DB. Returns (html, connect mock, cursor mock)."""
    conn = search_conn(list(rows))
    query_string = None if q is None else {"q": q}
    with patch("app.psycopg2.connect", return_value=conn) as connect:
        resp = client.get("/search", query_string=query_string)
    assert resp.status_code == 200
    return resp.data.decode(), connect, conn.cursor.return_value


@pytest.mark.parametrize("raw, expected", [
    ("Pizza", ["pizza"]),
    ("  pizza   QUEEN st w ", ["pizza", "queen"]),
    ("pizza Pizza", ["pizza"]),
    ("ab", []),
    ("a b c", []),
    ("", []),
    (None, []),
    ("one two three four five six seven", ["one", "two", "three", "four", "five"]),
    ("x" * 150, ["x" * 100]),
])
def test_search_terms(raw, expected):
    assert app_module.search_terms(raw) == expected


@pytest.mark.parametrize("term, prefix, expected", [
    ("pizza", False, "%pizza%"),
    ("pizza", True, "pizza%"),
    ("100%", False, "%100\\%%"),
    ("a_b", False, "%a\\_b%"),
    ("back\\slash", False, "%back\\\\slash%"),
])
def test_like_pattern_escapes_wildcards(term, prefix, expected):
    assert app_module.like_pattern(term, prefix=prefix) == expected


@pytest.mark.parametrize("q", [None, "", "   "])
def test_empty_query_shows_hint_without_db(client, q):
    html, connect, _ = _search(client, q)
    assert "Search restaurants</h2>" in html
    assert HINT in html
    connect.assert_not_called()


def test_short_words_only_asks_for_three_characters_without_db(client):
    html, connect, _ = _search(client, "ab c")
    assert "Type a word of at least 3 characters." in html
    connect.assert_not_called()


def test_results_render_cards_linking_to_history(client):
    rows = [_result(1), _result(2, name="Pizza Nova", status="Conditional Pass", unit="Unit 2")]
    html, _, _ = _search(client, "pizza", rows)
    assert 'Results for "pizza"' in html
    assert "2 restaurants</span>" in html
    assert html.count('class="result-card') == 2
    assert 'href="/establishment/001Vo0000000000001"' in html
    assert 'class="result-card status-conditional"' in html
    assert "123 Queen St W Unit 2" in html
    assert '<span class="label">Last inspected</span> October 3, 2026' in html
    assert '<strong class="status-badge">CONDITIONAL PASS</strong>' in html
    assert "14 inspections since 2019" in html
    assert html.index("Pizza Pizza") < html.index("Pizza Nova")


def test_one_result_is_singular(client):
    html, _, _ = _search(client, "pizza", [_result()])
    assert "1 restaurant</span>" in html


def test_result_without_type_hides_type(client):
    html, _, _ = _search(client, "pizza", [_result(est_type=None)])
    assert "None" not in html
    assert '<span class="est-type">Restaurant</span>' not in html


def test_no_matches_shows_message_and_hint(client):
    html, _, _ = _search(client, "zzzz")
    assert '<span class="heading-dates">0 restaurants</span>' in html
    assert 'No restaurants match "zzzz".' in html
    assert HINT in html


def test_search_sql_has_no_user_input(client):
    _, _, cur = _search(client, "Pizza'; DROP TABLE inspections;--", [_result()])
    (count, count_params), (pins, pin_params), (query, params) = (
        c.args for c in cur.execute.call_args_list
    )
    for sql_text in (count.as_string(None), pins.as_string(None), query.as_string(None)):
        assert "drop table" not in sql_text.lower()
        assert "pizza" not in sql_text
    # 4 words, 2 patterns each; the page adds the prefix pattern, limit and offset.
    assert count.as_string(None).count("%s") == 8
    assert count_params == params[:8]
    assert query.as_string(None).count("%s") == 11
    assert params[:2] == ["%pizza';%", "%pizza';%"]
    assert params[-3:] == ["pizza';%", 50, 0]
    # The map query adds the prefix pattern and the pin limit.
    assert pins.as_string(None).count("%s") == 10
    assert pin_params == count_params + ["pizza';%", 1000]


def test_query_is_html_escaped(client):
    html, _, _ = _search(client, "<script>alert(1)</script>")
    assert "<script>alert(1)" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_search_page_is_noindex_with_title(client):
    html, _, _ = _search(client, "pizza", [_result()])
    assert '<meta name="robots" content="noindex, nofollow">' in html
    assert 'content="noindex">' not in html
    assert "<title>DineSafeViz - Search</title>" in html


@pytest.mark.parametrize("q", ["abc\x00", "\x00abc", "abc\x1f\x7f"])
def test_control_characters_are_stripped_before_searching(client, q):
    # psycopg2 refuses NUL in a parameter (ValueError, so a 500); strip it first.
    html, connect, cur = _search(client, q)
    connect.assert_called_once()
    _, params = cur.execute.call_args.args
    assert params == ["%abc%", "%abc%"]
    assert 'No restaurants match "abc".' in html


def test_nul_in_query_returns_200(client):
    conn = search_conn([])

    def execute(_query, params):
        # Real psycopg2 raises this for a NUL in any string parameter.
        if any("\x00" in p for p in params if isinstance(p, str)):
            raise ValueError("A string literal cannot contain NUL (0x00) characters.")

    conn.cursor.return_value.execute.side_effect = execute
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get("/search?q=abc%00")
    assert resp.status_code == 200


def test_null_name_renders_dash_not_none(client):
    html, _, _ = _search(client, "pizza", [_result(name=None)])
    assert "<strong>—</strong>" in html
    assert "<strong>None</strong>" not in html


def test_longdate_filter():
    f = app_module.app.jinja_env.filters["longdate"]
    assert f(date(2026, 10, 3)) == "October 3, 2026"
    assert f(date(2026, 1, 15)) == "January 15, 2026"


def test_search_result_last_inspected_long_date(client):
    html, _, _ = _search(client, "pizza", [_result()])
    assert "October 3, 2026" in html
