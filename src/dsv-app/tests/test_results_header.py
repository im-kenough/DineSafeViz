"""Search content sits in a .results-section set off from the nav by a divider,
and the establishment heading splits address and inspections summary (#357)."""
import re
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import rows_conn, search_conn

_STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"
EST_ID = "001Vo000013QjdPIAS"


def _search_result(n=1):
    return {
        "establishment_id": f"001Vo0000000000{n:03d}",
        "establishment_name": "Pizza Pizza",
        "street": "123 Queen St W",
        "unit": None,
        "establishment_status": "Pass",
        "last_inspected": date(2026, 10, 3),
        "inspection_count": 14,
        "first_inspected": date(2019, 3, 4),
        "establishment_type": None,
    }


def _inspection(day, name="Pizza Pizza", unit=None):
    """One row as returned by _fetch_establishment's RealDictCursor query."""
    return {
        "inspection_date": day,
        "establishment_status": "Pass",
        "action": None,
        "infraction_details": None,
        "establishment_name": name,
        "establishment_address": "123 Queen St W M5V 2A1",
        "establishment_type": None,
        "street": "123 Queen St W",
        "unit": unit,
        "postal_code": None,
        "outcome": None,
        "outcome_date": None,
        "amount_fined": None,
        "establishment_id": EST_ID,
        "severity": None,
        "infraction_category": None,
    }


def _get(client, url, rows=(), total=None):
    rows = list(rows)
    conn = search_conn(rows, total) if url.startswith("/search") else rows_conn(rows)
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get(url)
    assert resp.status_code == 200
    return resp.data.decode()


def _css_rules(css):
    """(selectors, body) pairs for the plain rules in css, comments stripped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return re.findall(r"([^{}]+)\{([^}]*)\}", css)


def _css_rule(selector, css=None):
    """Body of the first style.css rule whose selector list includes selector."""
    for selectors, body in _css_rules(css if css is not None else _STYLE_CSS.read_text()):
        if selector in (" ".join(s.split()) for s in selectors.split(",")):
            return body
    return None


def _media_block(query):
    """Inner text of the first `@media <query>` block in style.css."""
    css = _STYLE_CSS.read_text()
    start = css.index("{", css.index(f"@media {query}")) + 1
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return css[start:i - 1]


@pytest.mark.parametrize("q, rows, total", [
    ("", [], None),
    ("ab c", [], None),
    ("zzzz", [], None),
    ("pizza", [_search_result(1), _search_result(2)], None),
    ("pizza", [_search_result(n) for n in range(app_module.SEARCH_LIMIT)], 157),
], ids=["empty", "short-words", "no-matches", "results", "more-than-limit"])
def test_search_content_inside_results_section(client, q, rows, total):
    html = _get(client, f"/search?q={q}", rows, total)
    assert html.count('<section class="results-section">') == 1
    start = html.index('<section class="results-section">')
    end = html.index("</section>", start)
    assert start < html.index('<h2 class="page-heading">') < end
    for tag in ('<p class="no-data">', '<ul class="results">', '<nav class="pager"'):
        if tag in html:
            assert start < html.index(tag) < end


def test_results_section_css_has_divider_and_padding():
    rule = _css_rule(".results-section")
    assert rule is not None
    assert "border-top: 1px solid var(--border)" in rule
    padding = re.search(r"padding-top:\s*([^;]+)", rule)
    assert padding and not re.fullmatch(r"0(\.0*)?[a-z%]*", padding.group(1).strip())


def test_establishment_heading_splits_address_and_summary(client):
    rows = [_inspection(date(2019, 3, 4)), _inspection(date(2026, 10, 3), unit="Unit 2")]
    html = _get(client, f"/establishment/{EST_ID}", rows)
    spans = ('<span class="heading-address">123 Queen St W Unit 2, Toronto, ON</span>'
             '<span class="heading-dates">2 inspections, March 4, 2019 to October 3, 2026</span>')
    assert spans in html
    heading = re.search(r'<h2 class="page-heading">(.*?)</h2>', html, flags=re.S).group(1)
    assert spans in heading
    assert " · " not in heading


def test_establishment_heading_one_inspection(client):
    html = _get(client, f"/establishment/{EST_ID}", [_inspection(date(2026, 10, 3))])
    assert '<span class="heading-dates">1 inspection, October 3, 2026</span>' in html


def test_heading_address_css_block_in_text_colour():
    rule = _css_rule(".heading-address")
    assert rule is not None
    assert "display: block" in rule
    address_colour = [body for sel, body in _css_rules(_STYLE_CSS.read_text())
                      if ".heading-address" in (" ".join(s.split()) for s in sel.split(","))
                      and "color:" in body]
    assert any("color: var(--text)" in body for body in address_colour)
    dates_colour = [body for sel, body in _css_rules(_STYLE_CSS.read_text())
                    if ".heading-dates" in (" ".join(s.split()) for s in sel.split(","))
                    and "color:" in body]
    assert any("color: var(--text-muted)" in body for body in dates_colour)


def test_heading_address_matches_dates_size_on_mobile():
    mobile = _media_block("(max-width: 600px)")
    address = _css_rule(".heading-address", mobile)
    dates = _css_rule(".heading-dates", mobile)
    assert address is not None and dates is not None
    size = re.search(r"font-size:\s*([^;]+)", dates).group(1).strip()
    assert re.search(rf"font-size:\s*{re.escape(size)}", address)


@pytest.mark.parametrize("selector", [".results-section", ".heading-address"])
def test_new_rules_have_no_hex_colours(selector):
    for sel, body in _css_rules(_STYLE_CSS.read_text()):
        if selector in (" ".join(s.split()) for s in sel.split(",")):
            assert "#" not in body
