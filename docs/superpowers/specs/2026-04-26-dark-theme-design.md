# Dark Theme & CSS Extraction — Design Spec

**Date:** 2026-04-26
**Branch:** dev-app

## Overview

Extract all inline CSS from `index.html` into a single static stylesheet, apply a dark theme, and add severity-based row color coding via CSS classes.

## Goals

- All styles live in one file: `src/web/static/style.css`
- Dark theme with a palette that lets the color-coded severity rows be the visual focal point
- Row backgrounds shaded at 60% opacity per severity level
- No external fonts, no external assets, no new dependencies
- No Python changes

## File Structure

```
src/web/
  static/
    style.css          ← new; all styles moved here
  templates/
    index.html         ← <style> block replaced with <link>
```

Flask serves `static/` at `/static/` automatically. The template references it via:
```html
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
```

## Color Palette

All values defined as CSS custom properties in `:root`:

| Variable            | Value                    | Use                          |
|---------------------|--------------------------|------------------------------|
| `--bg`              | `#0e1016`                | Page background              |
| `--surface`         | `#161920`                | Day-box background           |
| `--surface-2`       | `#1d2028`                | Table header cell background |
| `--border`          | `#262a35`                | All borders                  |
| `--text`            | `#dde1ec`                | Primary text                 |
| `--text-muted`      | `#5e6478`                | `th` labels, day heading, no-data |
| `--accent`          | `#4a7aff`                | Active tab border            |

## Severity Row Colors

CSS class applied to each `<tr>`, background at 60% opacity:

| Class              | Severity value      | Color                        |
|--------------------|---------------------|------------------------------|
| `sev-crucial`      | C - Crucial         | `rgba(220, 38,  38,  0.6)`   |
| `sev-significant`  | S - Significant     | `rgba(234, 88,  12,  0.6)`   |
| `sev-minor`        | M - Minor           | `rgba(202, 138,  4,  0.6)`   |
| `sev-na`           | NA                  | `rgba( 22, 163, 74,  0.6)`   |
| `sev-none`         | None                | `rgba( 37,  99, 235, 0.6)`   |

Rows with an unrecognised severity value get no class (no background change).

## CSS File Structure

Sections in `style.css`:

1. `:root` — custom properties
2. Base — `body`, `h1`
3. Tabs — `.tabs`, `.tabs a`, `.active`, `:hover`
4. Day-box — `.day-box`, `.day-box h2`, `.no-data`
5. Table — `table`, `th`, `td`
6. Severity — `tr.sev-crucial` … `tr.sev-none`

## Template Changes

### Remove `<style>` block, add `<link>`

```html
<link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
```

### Add severity class to each `<tr>`

Define a mapping dict once before the row loop:

```jinja2
{% set sev_class = {
  'C - Crucial':     'sev-crucial',
  'S - Significant': 'sev-significant',
  'M - Minor':       'sev-minor',
  'NA':              'sev-na',
  'None':            'sev-none'
} %}
```

Apply on the row element:

```jinja2
<tr class="{{ sev_class.get(row.severity, '') }}">
```

## Out of Scope

- Font changes (existing `sans-serif` stack unchanged)
- Any layout or structural changes beyond styling
- Inline styles or `<style>` blocks on any element
- New routes, Python logic, or data model changes
