"""Search results sit in a 3/2/1 column grid of stacked cards, CSS only (#363)."""
import re
from functools import cache
from unittest.mock import patch

import pytest

import app as app_module
from db_fakes import search_conn, search_row
from style_css import block_end, css_decls, css_rules, css_text, media_block

_GRID_SELECTORS = (".results", ".results > li", ".result-card")


def _search(client, q="pizza", page=None, total=157, rows=()):
    query_string = {"q": q} if page is None else {"q": q, "page": page}
    with patch("app.psycopg2.connect", return_value=search_conn(list(rows), total)):
        resp = client.get("/search", query_string=query_string)
    assert resp.status_code == 200
    return resp.data.decode()


@cache
def _top_level_css():
    """style.css without comments or @media blocks, so only base rules remain."""
    css = css_text()
    while (at := css.find("@media")) != -1:
        css = css[:at] + css[block_end(css, css.index("{", at) + 1):]
    return css


def _own_rule(selector, css=None):
    """Body of the first rule whose whole selector list is exactly selector."""
    for selectors, body in css_rules(_top_level_css() if css is None else css):
        if ", ".join(selectors) == selector:
            return " ".join(body.split())
    return None


def test_results_base_grid_has_three_columns():
    rule = _own_rule(".results")
    assert rule is not None
    assert "display: grid" in rule
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in rule
    assert "gap:" in rule


def test_results_grid_has_two_columns_below_desktop():
    rule = _own_rule(".results", media_block("(max-width: 1023px)"))
    assert rule is not None
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in rule


def test_results_grid_has_one_column_on_mobile():
    rule = _own_rule(".results", media_block("(max-width: 600px)"))
    assert rule is not None
    assert "grid-template-columns: minmax(0, 1fr)" in rule


def test_results_items_stretch_card_to_row_height():
    rule = _own_rule(".results > li")
    assert rule is not None
    if "display: flex" in rule:
        assert "flex: 1" in _own_rule(".result-card")
    else:
        assert "display: grid" in rule


def test_result_card_spacing_comes_from_gap_only():
    assert css_decls(_own_rule(".result-card")).get("margin-bottom") == "0"
    assert css_decls(_own_rule(".est-card, .result-card")).get("margin-bottom") == "0.6rem"


def test_result_cards_stack_at_every_width():
    card = _own_rule(".result-card")
    latest = _own_rule(".result-latest")
    badge = _own_rule(".result-latest .status-badge")
    assert css_decls(card).get("grid-template-columns") == "1fr"
    assert "1fr auto" not in card
    assert "text-align: left" in latest
    assert "text-align: right" not in latest
    assert "align-self: flex-start" in badge
    assert "flex-end" not in badge


def test_long_text_cannot_widen_a_card():
    card = _own_rule(".result-card")
    assert "overflow-wrap: anywhere" in card or "min-width: 0" in card


@pytest.mark.parametrize("selector", [".results", ".result-card"])
def test_grid_keeps_dom_reading_order(selector):
    for selectors, body in css_rules():
        if selector in selectors:
            assert not re.search(r"(^|[;\s])order\s*:", body)
            assert "dense" not in body


def test_full_page_renders_one_list_with_pager_outside(client):
    html = _search(client, rows=[search_row(n, name=f"Pizza {n}") for n in range(app_module.SEARCH_LIMIT)], total=157)
    assert app_module.SEARCH_LIMIT == 50
    assert html.count('<ul class="results">') == 1
    start = html.index('<ul class="results">')
    end = html.index("</ul>", start)
    inside = html[start:end]
    assert inside.count("<li>") == 50
    assert '<nav class="pager"' not in inside
    assert 'class="no-data"' not in inside
    assert html.index('<nav class="pager"') > end


@pytest.mark.parametrize("q, page, total", [
    ("", None, 0),
    ("ab", None, 0),
    ("zzzz", None, 0),
    ("pizza", 9, 157),
])
def test_no_data_messages_sit_outside_results_list(client, q, page, total):
    html = _search(client, q=q, page=page, total=total)
    assert 'class="no-data"' in html
    assert '<ul class="results">' not in html


@pytest.mark.parametrize("selector", _GRID_SELECTORS)
def test_grid_rules_add_no_hex_colours(selector):
    for selectors, body in css_rules():
        if ", ".join(selectors) == selector:
            assert "#" not in body
