"""Search bar border and clearer home page buttons (#362): a visible input
border, a filled hero Search button, Explore cards that look clickable."""
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from db_fakes import search_conn

_APP = Path(__file__).resolve().parent.parent
_STYLE_CSS = _APP / "static" / "style.css"
_HOME_HTML = _APP / "templates" / "home.html"
_HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def _css_rules(css):
    """(selectors, body) pairs for the plain rules in css, comments stripped."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [
        (tuple(" ".join(s.split()) for s in selectors.split(",")), body)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    ]


def _rule(rules, selector):
    """Body of the first rule whose selector list includes selector."""
    return next((body for selectors, body in rules if selector in selectors), None)


def _decls(body):
    """Declarations of a rule body as a {property: value} dict."""
    return {
        prop.strip(): value.strip()
        for prop, value in (d.split(":", 1) for d in body.split(";") if d.strip())
    }


def _style_rules():
    return _css_rules(_STYLE_CSS.read_text())


def _home_rules(client):
    html = client.get("/").data.decode()
    return _css_rules(html[html.index("<style>") + 7:html.index("</style>")])


def _home_explore(client):
    html = client.get("/").data.decode()
    section = html[html.index('<section class="day-box explore"'):]
    return section[:section.index("</section>")]


def test_search_input_border_uses_text_muted():
    body = _rule(_style_rules(), ".search-form input")
    assert _decls(body)["border"] == "1px solid var(--text-muted)"
    assert "var(--border)" not in body


def test_hero_search_button_is_filled_with_accent():
    rules = _style_rules()
    decls = _decls(_rule(rules, ".hero-search button"))
    assert decls["background"] == "var(--accent)"
    assert decls["color"] == "var(--bg)"
    # comes after the shared .search-form button rule
    order = [selectors for selectors, _ in rules]
    assert order.index((".hero-search button",)) > order.index((".search-form button",))


def test_search_macro_button_stays_nav_btn():
    macro = (_APP / "templates" / "_search.html").read_text()
    assert '<button type="submit" class="nav-btn">Search</button>' in macro


def test_hero_button_hover_left_to_nav_btn_rule():
    rules = _style_rules()
    assert "!important" not in _rule(rules, ".hero-search button")
    assert not [s for selectors, _ in rules for s in selectors if "hero-search" in s and ":hover" in s]
    assert _decls(_rule(rules, ".nav-btn:hover:not(.active)"))["background"] == "#2952d9"


def test_explore_cards_have_call_to_action(client):
    explore = _home_explore(client)
    cards = re.findall(r'<a href="([^"]+)" class="day-box nav-card">(.*?)</a>', explore, flags=re.S)
    assert [href for href, _ in cards] == ["/inspections", "/dashboard"]
    assert '<span class="nav-cta">View inspections <span aria-hidden="true">→</span></span>' in cards[0][1]
    assert '<span class="nav-cta">Open dashboard <span aria-hidden="true">→</span></span>' in cards[1][1]


def test_nav_cta_style(client):
    decls = _decls(_rule(_home_rules(client), ".nav-cta"))
    assert decls["color"] == "var(--text)"
    assert decls["font-weight"] == "600"
    assert decls["text-decoration"] == "underline"
    assert decls["text-decoration-color"] == "var(--accent)"


def test_nav_card_hover_and_focus_highlight_whole_card(client):
    rules = _home_rules(client)
    hover = [body for selectors, body in rules if selectors == (".nav-card:hover", ".nav-card:focus-visible")]
    assert len(hover) == 1
    assert _decls(hover[0])["box-shadow"] == "inset 0 0 0 1px var(--accent)"
    focus = [body for selectors, body in rules if selectors == (".nav-card:focus-visible",)]
    assert len(focus) == 1
    assert _decls(focus[0]) == {"outline": "2px solid var(--text)", "outline-offset": "2px"}
    # the h3 accent hover stays
    h3 = _rule(rules, ".nav-card:hover h3")
    assert _decls(h3)["color"] == "var(--accent)"


def test_no_new_hex_colours(client):
    assert not _HEX.search(_HOME_HTML.read_text())
    style_rules = _style_rules()
    # hex colours in style.css live only in :root and the two pre-existing hover rules
    with_hex = [selectors for selectors, body in style_rules if _HEX.search(body)]
    assert with_hex == [
        (":root",),
        (".nav-btn.active", ".nav-btn:hover:not(.active)"),
        (".timeline .month-link.current:hover",),
    ]
    new_rules = [_rule(style_rules, ".hero-search button"), _rule(_home_rules(client), ".nav-cta")]
    for body in new_rules:
        for prop, value in _decls(body).items():
            if "color" in prop or prop == "background":
                assert value.startswith("var(--"), (prop, value)


@pytest.mark.parametrize("url", ["/info", "/search?q=pizza", "/no-such-page"])
def test_nav_search_button_stays_outline(client, url):
    with patch("app.psycopg2.connect", return_value=search_conn([])):
        html = client.get(url).data.decode()
    form = html[html.index('<form class="search-form nav-search"'):]
    form = form[:form.index("</form>")]
    assert '<button type="submit" class="nav-btn">Search</button>' in form
