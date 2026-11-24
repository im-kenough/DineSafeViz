"""nginx sends a CSP with script-src 'self' (no inline scripts), so every
executable <script> in the templates must load a file from /static."""
import re
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "templates"
SCRIPT_TAG = re.compile(r"<script\b([^>]*)>", re.I)


def test_templates_have_no_inline_scripts():
    inline = []
    for path in sorted(TEMPLATES.glob("*.html")):
        for attrs in SCRIPT_TAG.findall(path.read_text()):
            if "src=" in attrs or 'type="application/json"' in attrs:
                continue
            inline.append(path.name)
    assert inline == []


def test_templates_have_no_inline_event_handlers():
    for path in sorted(TEMPLATES.glob("*.html")):
        assert not re.search(r"<[^>]+\son[a-z]+=", path.read_text()), path.name
