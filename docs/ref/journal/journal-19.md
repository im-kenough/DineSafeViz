# Journal 19

## 2026-04-28 — Planning responsive layout optimization for QHD/FHD/HD

Task: optimize `style.css` and `base.html` for three desktop breakpoints:
- 2560×1440 (QHD)
- 1920×1080 (Full HD)
- 1280×720 (HD)

### Current state audit

- `body`: `max-width: 1200px`, `margin: 2rem` — NOT centered (no `auto` horizontal margin)
- No media queries anywhere
- Fixed font sizes (px/rem absolute values)
- No table overflow handling
- Nav (`flex-wrap: wrap`) is reasonably robust but untested at scale

### Issues identified

1. **Not centered**: `margin: 2rem` (no `auto`) means content is left-aligned 32px from left edge on all screens
2. **Too narrow at QHD**: 1200px max-width leaves ~680px of empty space on each side at 2560px
3. **Typography doesn't scale**: `h1` at `2rem`, body at `sans-serif` default (~16px) — looks small at QHD
4. **Tables overflow silently**: No horizontal scroll wrapper; wide tables clip or cause body overflow
5. **Spacing too tight at QHD**: `padding: 0.35rem 0.6rem` in table cells, `1rem` day-box padding designed for ~1200px

### Plan filed

## 2026-04-28 — Implemented responsive changes

Files edited:
- `src/dsv-app/static/style.css`: centered body (margin auto + padding), added ≥1400px and ≥2200px max-width breakpoints, clamp() on h1/nav-btn/th-td font sizes, .table-wrap overflow rule, QHD spacing block
- `src/dsv-app/templates/index.html`: wrapped `<table>` in `<div class="table-wrap">`

Changes: 6 edits, ~20 lines added to CSS, 2 lines added to index.html
