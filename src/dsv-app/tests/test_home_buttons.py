"""Search bar border and clearer home page buttons (#362): a visible input
border, a filled hero Search button, Explore cards that look clickable."""
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from db_fakes import search_conn
from style_css import css_decls, css_rule, css_rules

_APP = Path(__file__).resolve().parent.parent
_HOME_HTML = _APP / "templates" / "home.html"
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _home_css(client):
    """The <style> block in the rendered home page."""
    html = client.get("/").data.decode()
    return html[html.index("<style>") + 7:html.index("</style>")]


def _home_explore(client):
    html = client.get("/").data.decode()
    section = html[html.index('<section class="day-box explore"'):]
    return section[:section.index("</section>")]


def test_search_input_border_uses_text_muted():
    body = css_rule(".search-form input")
    assert css_decls(body)["border"] == "1px solid var(--text-muted)"
    assert "var(--border)" not in body


def test_hero_search_button_is_filled_with_accent():
    decls = css_decls(css_rule(".hero-search button"))
    assert decls["background"] == "var(--accent)"
    assert decls["color"] == "var(--bg)"
    # comes after the shared .search-form button rule
    order = [selectors for selectors, _ in css_rules()]
    assert order.index((".hero-search button",)) > order.index((".search-form button",))


def test_search_macro_button_stays_nav_btn():
    macro = (_APP / "templates" / "_search.html").read_text()
    assert '<button type="submit" class="nav-btn">Search</button>' in macro


def test_hero_button_hover_left_to_nav_btn_rule():
    assert "!important" not in css_rule(".hero-search button")
    assert not [s for selectors, _ in css_rules() for s in selectors if "hero-search" in s and ":hover" in s]
    assert css_decls(css_rule(".nav-btn:hover:not(.active)"))["background"] == "#2952d9"


def test_explore_cards_have_call_to_action(client):
    explore = _home_explore(client)
    cards = re.findall(r'<a href="([^"]+)" class="day-box nav-card">(.*?)</a>', explore, flags=re.S)
    assert [href for href, _ in cards] == ["/inspections", "/dashboard"]
    assert '<span class="nav-cta">View inspections <span aria-hidden="true">→</span></span>' in cards[0][1]
    assert '<span class="nav-cta">Open dashboard <span aria-hidden="true">→</span></span>' in cards[1][1]


def test_nav_cta_style(client):
    decls = css_decls(css_rule(".nav-cta", _home_css(client)))
    assert decls["color"] == "var(--text)"
    assert decls["font-weight"] == "600"
    assert decls["text-decoration"] == "underline"
    assert decls["text-decoration-color"] == "var(--accent)"


def test_nav_card_hover_and_focus_highlight_whole_card(client):
    home = _home_css(client)
    rules = css_rules(home)
    hover = [body for selectors, body in rules if selectors == (".nav-card:hover", ".nav-card:focus-visible")]
    assert len(hover) == 1
    assert css_decls(hover[0])["box-shadow"] == "inset 0 0 0 1px var(--accent)"
    focus = [body for selectors, body in rules if selectors == (".nav-card:focus-visible",)]
    assert len(focus) == 1
    assert css_decls(focus[0]) == {"outline": "2px solid var(--text)", "outline-offset": "2px"}
    # the h3 accent hover stays
    h3 = css_rule(".nav-card:hover h3", home)
    assert css_decls(h3)["color"] == "var(--accent)"


def test_no_new_hex_colours(client):
    assert not _HEX.search(_HOME_HTML.read_text())
    # hex colours in style.css live only in :root and the two pre-existing hover rules
    with_hex = [selectors for selectors, body in css_rules() if _HEX.search(body)]
    assert with_hex == [
        (":root",),
        (".nav-btn.active", ".nav-btn:hover:not(.active)"),
        (".timeline .month-link.current:hover",),
    ]
    new_rules = [css_rule(".hero-search button"), css_rule(".nav-cta", _home_css(client))]
    for body in new_rules:
        for prop, value in css_decls(body).items():
            if "color" in prop or prop == "background":
                assert value.startswith("var(--"), (prop, value)


@pytest.mark.parametrize("url", ["/info", "/search?q=pizza", "/no-such-page"])
def test_nav_search_button_stays_outline(client, url):
    with patch("app.psycopg2.connect", return_value=search_conn([])):
        html = client.get(url).data.decode()
    form = html[html.index('<form class="search-form nav-search"'):]
    form = form[:form.index("</form>")]
    assert '<button type="submit" class="nav-btn">Search</button>' in form
