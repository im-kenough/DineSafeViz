"""Search content sits in a .results-section set off from the nav by a divider,
and the establishment heading splits address and inspections summary (#357)."""
import re
from datetime import date
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import EST_ID, inspection_row, rows_conn, search_conn, search_row
from style_css import css_rule, css_rules, media_block


def _get(client, url, rows=(), total=None):
    rows = list(rows)
    conn = search_conn(rows, total) if url.startswith("/search") else rows_conn(rows)
    with patch("app.psycopg2.connect", return_value=conn):
        resp = client.get(url)
    assert resp.status_code == 200
    return resp.data.decode()


@pytest.mark.parametrize("q, rows, total", [
    ("", [], None),
    ("ab c", [], None),
    ("zzzz", [], None),
    ("pizza", [search_row(1), search_row(2)], None),
    ("pizza", [search_row(n) for n in range(app_module.SEARCH_LIMIT)], 157),
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
    rule = css_rule(".results-section")
    assert rule is not None
    assert "border-top: 1px solid var(--border)" in rule
    padding = re.search(r"padding-top:\s*([^;]+)", rule)
    assert padding and not re.fullmatch(r"0(\.0*)?[a-z%]*", padding.group(1).strip())


def test_establishment_heading_splits_address_and_summary(client):
    rows = [inspection_row(date(2019, 3, 4)), inspection_row(date(2026, 10, 3), unit="Unit 2")]
    html = _get(client, f"/establishment/{EST_ID}", rows)
    spans = ('<span class="heading-address">123 Queen St W Unit 2, Toronto, ON</span>'
             '<span class="heading-dates">2 inspections, March 4, 2019 to October 3, 2026</span>')
    assert spans in html
    heading = re.search(r'<h2 class="page-heading">(.*?)</h2>', html, flags=re.S).group(1)
    assert spans in heading
    assert " · " not in heading


def test_establishment_heading_one_inspection(client):
    html = _get(client, f"/establishment/{EST_ID}", [inspection_row(date(2026, 10, 3))])
    assert '<span class="heading-dates">1 inspection, October 3, 2026</span>' in html


def test_heading_address_css_block_in_text_colour():
    rule = css_rule(".heading-address")
    assert rule is not None
    assert "display: block" in rule
    address_colour = [body for sel, body in css_rules() if ".heading-address" in sel and "color:" in body]
    assert any("color: var(--text)" in body for body in address_colour)
    dates_colour = [body for sel, body in css_rules() if ".heading-dates" in sel and "color:" in body]
    assert any("color: var(--text-muted)" in body for body in dates_colour)


def test_heading_address_matches_dates_size_on_mobile():
    mobile = media_block("(max-width: 600px)")
    address = css_rule(".heading-address", mobile)
    dates = css_rule(".heading-dates", mobile)
    assert address is not None and dates is not None
    size = re.search(r"font-size:\s*([^;]+)", dates).group(1).strip()
    assert re.search(rf"font-size:\s*{re.escape(size)}", address)


@pytest.mark.parametrize("selector", [".results-section", ".heading-address"])
def test_new_rules_have_no_hex_colours(selector):
    for sel, body in css_rules():
        if selector in sel:
            assert "#" not in body
