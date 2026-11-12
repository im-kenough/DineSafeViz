"""Shared a11y fixes from base.html and style.css (issue #361): muted text
contrast, a <main> landmark on every page, 44px top nav buttons."""
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from db_fakes import rows_conn, search_conn

_STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"


def _css_rule(selector):
    """Body of the first style.css rule whose selector list includes selector."""
    css = re.sub(r"/\*.*?\*/", "", _STYLE_CSS.read_text(), flags=re.S)
    for selectors, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        if selector in (" ".join(s.split()) for s in selectors.split(",")):
            return body
    return None


def test_text_muted_meets_contrast():
    assert re.search(r"--text-muted:\s*#83899d;", _css_rule(":root"))
    assert "#7a8094" not in _STYLE_CSS.read_text().lower()


# (url, fake DB connection or None, text that must sit inside <main>)
_PAGES = [
    ("/", None, "Find restaurants that pass inspection"),
    ("/info", None, "Types of infractions"),
    ("/dashboard", None, "<iframe"),
    ("/inspections?year=2024&q=1", rows_conn([]), 'class="page-heading"'),
    ("/search?q=pizza", search_conn([]), 'Results for "pizza"'),
    ("/no-such-page", None, "Page not found"),
]


@pytest.mark.parametrize("url,db,content", _PAGES)
def test_page_has_one_main_landmark_around_content(client, url, db, content):
    with patch("app.psycopg2.connect", return_value=db or rows_conn([])):
        html = client.get(url).data.decode()
    assert html.count("<main") == 1
    assert html.count("</main>") == 1
    nav_end = html.index("</nav>")
    main_start = html.index("<main")
    main_end = html.index("</main>")
    assert nav_end < main_start < main_end < html.index("<footer")
    assert content in html[main_start:main_end]


def test_top_nav_buttons_are_44px_tap_targets():
    body = _css_rule(".tabs > a")
    assert body is not None
    assert body == _css_rule(".dropdown > summary")
    decls = {k.strip(): v.strip() for k, v in
             (d.split(":", 1) for d in body.split(";") if d.strip())}
    assert decls["min-height"] == "44px"
    assert decls["box-sizing"] == "border-box"
    assert decls["display"] in ("flex", "inline-flex")
    assert decls["align-items"] == "center"
