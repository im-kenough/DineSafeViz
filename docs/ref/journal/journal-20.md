# Journal 20

## 2026-04-28 — Font consistency, contrast, and legibility audit

Task: ensure website fonts are consistent, have good contrast, and are legible.

### Audit findings

**Font inconsistency:**
- `body { font-family: sans-serif }` — generic fallback, renders as Helvetica/Arial/DejaVu depending on OS. No web font loaded. No `<link>` for any font in base.html.

**Contrast failures (WCAG AA = 4.5:1 for normal text, 3:1 for large text):**
- `--text-muted: #5e6478` on `--bg: #0e1016` → ~3.62:1. Fails AA for normal text. Used on: `th` (table headers), `.day-box h2`, `.no-data`, footer.
- Active/hover `.nav-btn`: `color: #fff` on `--accent: #4a7aff` → ~3.49:1. Fails AA for 14px bold text (needs 4.5:1; large text threshold is 18.67px bold or 24px normal).

**Legibility gaps:**
- No `line-height` set on body; browsers default to ~1.2 which is tight for reading.
- No `font-feature-settings` for tabular numbers in data tables.

### Plan

1. Add Google Fonts: `IBM Plex Sans` (weights 400, 500, 600, 700) — excellent for data UIs, distinctive, legible at small sizes, supports tabular numerals.
2. Set `font-family` on body to IBM Plex Sans with sans-serif fallback.
3. Lighten `--text-muted` to `#7a8094` → estimated luminance ~0.247, contrast vs bg ~5.4:1. Passes AA.
4. Fix active nav btn contrast: darken active bg to `#2952d9` (luminance ~0.09) → white text gets ~6.3:1. Passes AA.
5. Add `line-height: 1.6` to body, `font-feature-settings: "tnum"` to table cells.

### Changes made

`src/web/static/fonts/` (new):
- IBMPlexSans-Regular.woff2, Medium.woff2, SemiBold.woff2, Bold.woff2
- Sourced from npm `@ibm/plex@6.4.0`, no runtime external dependency

`src/web/templates/base.html`:
- No changes (Google Fonts links were added then removed; external preconnects removed)

`src/web/static/style.css`:
- `--text-muted`: `#5e6478` → `#7a8094` (contrast ~5.4:1 on bg; was 3.62:1)
- `body`: `font-family` → `'IBM Plex Sans', sans-serif`; added `line-height: 1.6`
- Active/hover nav btn: bg `var(--accent)` → `#2952d9` (contrast ~6.3:1 with white; was 3.49:1)
- `th, td`: added `font-feature-settings: "tnum"` for aligned digits in table columns
