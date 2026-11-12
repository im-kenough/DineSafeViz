"""Search shows the total match count and pages through results, 50 per page (#353)."""
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import search_conn

_STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"


def _result(n):
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": f"Pizza {n}",
        "street": "123 Queen St W",
        "unit": None,
        "establishment_status": "Pass",
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 14,
        "first_inspected": date(2019, 3, 4),
        "establishment_type": None,
    }


def _page(total, page):
    """The fake rows for one page of a search with total matches."""
    start = (page - 1) * app_module.SEARCH_LIMIT
    return [_result(n) for n in range(start, min(total, start + app_module.SEARCH_LIMIT))]


def _search(client, q="pizza", page=None, total=157, rows=None):
    """GET /search with a fake DB. Returns (html, cursor mock)."""
    query_string = {"q": q} if page is None else {"q": q, "page": page}
    conn = search_conn(_page(total, 1) if rows is None else rows, total)
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get("/search", query_string=query_string)
    assert resp.status_code == 200
    return resp.data.decode(), conn.cursor.return_value


def _pager(html):
    match = re.search(r'<nav class="pager" aria-label="Search result pages">(.*?)</nav>', html, flags=re.S)
    return match.group(1) if match else None


# -- SQL -----------------------------------------------------------------------

def test_count_query_counts_distinct_ids_with_match_params():
    query, params = app_module.search_count_query(["pizza", "queen"])
    text = query.as_string(None)
    assert "SELECT COUNT(DISTINCT establishment_id) AS total" in text
    assert "FROM inspections WHERE" in text
    assert "pizza" not in text and "queen" not in text
    assert text.count("%s") == 4
    assert params == ["%pizza%", "%pizza%", "%queen%", "%queen%"]
    page_query, page_params = app_module.search_query(["pizza", "queen"], 1)
    assert page_params[:4] == params


@pytest.mark.parametrize("page, offset", [(1, 0), (2, 50), (4, 150)])
def test_page_query_limit_and_offset_are_params(page, offset):
    query, params = app_module.search_query(["pizza"], page)
    text = query.as_string(None)
    assert "LIMIT %s OFFSET %s" in text
    assert params == ["%pizza%", "%pizza%", "pizza%", app_module.SEARCH_LIMIT, offset]


# -- page parsing and DB calls -------------------------------------------------

@pytest.mark.parametrize("raw", [None, "", "abc", "-1", "+2", "1.5", "²", "0", " 2", "1e3"])
def test_bad_page_gives_page_one(client, raw):
    html, cur = _search(client, page=raw)
    _, params = cur.execute.call_args.args
    assert params[-1] == 0
    assert '<span class="nav-btn active" aria-current="page">1</span>' in html


@pytest.mark.parametrize("raw, page", [(None, 1), ("abc", 1), ("0", 1), ("3", 3), ("007", 7), ("9" * 30, 10 ** 30 - 1)])
def test_parse_page(raw, page):
    assert app_module.parse_page(raw) == page


def test_huge_page_never_reaches_the_db(client):
    # Past the end, so no OFFSET too big for Postgres' bigint is ever sent.
    html, cur = _search(client, page="9" * 30, rows=[])
    assert cur.execute.call_count == 1
    assert f'<p class="no-data">No results on page {"9" * 30}.' in html


def test_page_too_long_for_int_is_not_a_500(client):
    # int() refuses strings over sys.get_int_max_str_digits() (4300) digits.
    html, _ = _search(client, page="9" * 5000)
    assert '<span class="nav-btn active" aria-current="page">1</span>' in html


def test_page_two_offsets_by_fifty(client):
    html, cur = _search(client, page="2", rows=_page(157, 2))
    assert cur.execute.call_count == 2
    _, params = cur.execute.call_args.args
    assert params[-2:] == [50, 50]
    assert html.count('class="result-card') == 50


@pytest.mark.parametrize("page", ["5", "9"])
def test_past_the_end_runs_only_the_count(client, page):
    html, cur = _search(client, page=page, rows=[])
    assert cur.execute.call_count == 1
    assert '<span class="heading-dates">157 restaurants</span>' in html
    assert f'<p class="no-data">No results on page {page}.' in html
    assert 'href="/search?q=pizza&amp;page=1"' in html
    assert _pager(html) is None


def test_zero_matches_runs_only_the_count(client):
    html, cur = _search(client, q="zzzz", total=0)
    assert cur.execute.call_count == 1
    assert '<span class="heading-dates">0 restaurants</span>' in html
    assert 'No restaurants match "zzzz".' in html
    assert _pager(html) is None


# -- heading -------------------------------------------------------------------

@pytest.mark.parametrize("total, text", [(157, "157 restaurants"), (1, "1 restaurant"), (50, "50 restaurants")])
def test_heading_shows_total(client, total, text):
    html, _ = _search(client, total=total)
    assert f'<span class="heading-dates">{text}</span>' in html
    assert "Showing the first" not in html
    assert "+ restaurants" not in html


# -- pager ---------------------------------------------------------------------

@pytest.mark.parametrize("total", [1, 50])
def test_one_page_has_no_pager(client, total):
    html, _ = _search(client, total=total)
    assert "pager" not in html


def test_pager_on_first_page(client):
    html, _ = _search(client)
    pager = _pager(html)
    assert pager is not None
    assert html.index("</ul>") < html.index('<nav class="pager"')
    assert '<span class="nav-btn disabled" aria-disabled="true" aria-label="Previous page">‹</span>' in pager
    assert '<span class="nav-btn active" aria-current="page">1</span>' in pager
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=2" rel="nofollow">2</a>' in pager
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=4" rel="nofollow">4</a>' in pager
    assert 'href="/search?q=pizza&amp;page=1"' not in pager
    assert re.search(r'<a class="nav-btn" href="/search\?q=pizza&amp;page=2"[^>]*aria-label="Next page"[^>]*>›</a>', pager)


def test_pager_on_last_page(client):
    html, _ = _search(client, page="4", rows=_page(157, 4))
    pager = _pager(html)
    assert '<span class="nav-btn active" aria-current="page">4</span>' in pager
    assert '<span class="nav-btn disabled" aria-disabled="true" aria-label="Next page">›</span>' in pager
    assert re.search(r'<a class="nav-btn" href="/search\?q=pizza&amp;page=3"[^>]*aria-label="Previous page"[^>]*>‹</a>', pager)


def test_pager_shows_gaps(client):
    html, _ = _search(client, page="5", total=1000)
    pager = _pager(html)
    numbers = re.findall(r">(\d+|…)</(?:a|span)>", pager)
    assert numbers == ["1", "…", "4", "5", "6", "…", "20"]


def test_pager_links_are_nofollow(client):
    html, _ = _search(client, page="2", rows=_page(157, 2))
    pager = _pager(html)
    links = re.findall(r"<a [^>]*>", pager)
    assert links
    assert len(links) == len([a for a in links if re.search(r'rel="[^"]*nofollow"', a)])
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=1" rel="prev nofollow" aria-label="Previous page">‹</a>' in pager
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=3" rel="next nofollow" aria-label="Next page">›</a>' in pager
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=1" rel="nofollow">1</a>' in pager
    assert '<a class="nav-btn" href="/search?q=pizza&amp;page=3" rel="nofollow">3</a>' in pager


@pytest.mark.parametrize("page", ["1", "4"])
def test_pager_spans_have_no_rel(client, page):
    html, _ = _search(client, page=page, rows=_page(157, int(page)))
    spans = re.findall(r"<span [^>]*>", _pager(html))
    assert any("disabled" in s for s in spans) and any("active" in s for s in spans)
    assert not any("rel=" in s for s in spans)


def test_pager_gap_is_aria_hidden(client):
    html, _ = _search(client, page="5", total=1000)
    pager = _pager(html)
    assert pager.count('<span aria-hidden="true">…</span>') == 2
    assert pager.count("…") == 2


@pytest.mark.parametrize("page, pages, window", [
    (5, 20, [1, None, 4, 5, 6, None, 20]),
    (1, 4, [1, 2, 3, 4]),
    (1, 2, [1, 2]),
    (2, 3, [1, 2, 3]),
    (1, 20, [1, 2, None, 20]),
    (20, 20, [1, None, 19, 20]),
    (4, 7, [1, 2, 3, 4, 5, 6, 7]),
])
def test_page_window(page, pages, window):
    assert app_module.page_window(page, pages) == window


def test_pager_links_keep_encoded_query(client):
    html, _ = _search(client, q="burger king")
    assert '<a class="nav-btn" href="/search?q=burger+king&amp;page=2" rel="nofollow">2</a>' in _pager(html)


def test_pager_links_escape_script(client):
    html, _ = _search(client, q="<script>alert(1)</script>")
    pager = _pager(html)
    assert "<script>" not in pager
    assert 'href="/search?q=%3Cscript%3Ealert(1)%3C/script%3E&amp;page=2"' in pager


# -- CSS -----------------------------------------------------------------------

def _css():
    return re.sub(r"/\*.*?\*/", "", _STYLE_CSS.read_text(), flags=re.S)


def _css_rule(selector):
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", _css()):
        if selector in (" ".join(s.split()) for s in selectors.split(",")):
            return body
    return None


def test_pager_css():
    pager = _css_rule(".pager")
    assert pager is not None
    assert "display: flex" in pager and "flex-wrap: wrap" in pager and "justify-content: center" in pager
    assert "var(--border)" in pager
    disabled = _css_rule(".nav-btn.disabled")
    assert disabled is not None
    assert "color: var(--text-muted)" in disabled
    assert "pointer-events: none" in disabled
    for body in (pager, disabled):
        assert "#" not in body


def test_pager_buttons_are_tap_sized():
    body = _css_rule(".pager .nav-btn")
    assert body is not None
    for decl in ("min-width: 44px", "min-height: 44px", "display: inline-flex",
                 "align-items: center", "justify-content: center"):
        assert decl in body
    assert "#" not in body


def test_pager_buttons_rule_is_not_in_media_block():
    css = _css()
    match = re.search(r"(?:^|[}\s])\.pager \.nav-btn\s*\{", css)
    assert match is not None
    before = css[:match.start()]
    assert before.count("{") == before.count("}")
