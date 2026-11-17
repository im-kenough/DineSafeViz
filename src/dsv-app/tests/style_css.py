"""Read rules out of static/style.css, or any CSS text, for the CSS tests."""
import functools
import re
from pathlib import Path

STYLE_CSS = Path(__file__).resolve().parent.parent / "static" / "style.css"


def _strip_comments(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


@functools.cache
def css_text():
    """style.css without comments, read once."""
    return _strip_comments(STYLE_CSS.read_text())


def css_rules(css=None):
    """(selectors, body) pairs for the plain rules in css (default: style.css),
    comments stripped. selectors is a tuple, each one whitespace-normalised."""
    css = css_text() if css is None else _strip_comments(css)
    return [
        (tuple(" ".join(s.split()) for s in selectors.split(",")), body)
        for selectors, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
    ]


def css_rule(selector, css=None):
    """Body of the first rule in css (default: style.css) whose selector list
    includes selector, or None."""
    return next((body for selectors, body in css_rules(css) if selector in selectors), None)


def block_end(css, start):
    """Index just past the `}` that closes the block whose body starts at start."""
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(css[i], 0)
        i += 1
    return i


def media_block(query):
    """Inner text of the first `@media <query>` block in style.css, comments stripped."""
    css = css_text()
    match = re.search(rf"@media\s+{re.escape(query)}\s*\{{", css)
    assert match, f"no @media {query} block"
    start = match.end()
    return css[start:block_end(css, start) - 1]


def css_decls(body):
    """{property: value} for the declarations in a rule body."""
    return {
        prop.strip(): value.strip()
        for prop, _, value in (d.partition(":") for d in body.split(";")) if value.strip()
    }
