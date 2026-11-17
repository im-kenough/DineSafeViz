"""Shared a11y fixes from base.html and style.css (issue #361): muted text
contrast, a <main> landmark on every page, 44px top nav buttons."""
import re
from unittest.mock import patch

import pytest

from db_fakes import rows_conn, search_conn
from style_css import STYLE_CSS, css_decls, css_rule


def test_text_muted_meets_contrast():
    assert re.search(r"--text-muted:\s*#83899d;", css_rule(":root"))
    assert "#7a8094" not in STYLE_CSS.read_text().lower()


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
    body = css_rule(".tabs > a")
    assert body is not None
    assert body == css_rule(".dropdown > summary")
    decls = css_decls(body)
    assert decls["min-height"] == "44px"
    assert decls["box-sizing"] == "border-box"
    assert decls["display"] in ("flex", "inline-flex")
    assert decls["align-items"] == "center"
