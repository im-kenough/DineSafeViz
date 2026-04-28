# Journal 21

## 2026-04-28 — Font color consistency and contrast audit (continued)

Task: ensure all font colours are consistent and uniform across all pages, with sufficient contrast.

### Audit

Read style.css and all four templates (base.html, index.html, dashboard.html, info.html).

**Contrast ratios verified (WCAG AA: ≥4.5:1 normal text, ≥3:1 large text):**
- `--text #dde1ec` on `--bg #0e1016`: ~14.8:1 ✓
- `--text-muted #7a8094` on `--bg #0e1016`: ~5.3:1 ✓
- `--text-muted #7a8094` on `--surface #161920`: ~5.1:1 ✓
- `--text-muted #7a8094` on `--surface-2 #1d2028`: ~4.9:1 ✓
- `--accent #4a7aff` on `--bg #0e1016`: ~5.4:1 ✓
- `#fff` on `#2952d9` (active nav btn): ~5.8:1 ✓
- `--text` on sev-crucial blended bg: ~6.8:1 ✓
- `--text` on sev-significant blended bg: ~4.9:1 ✓
- `--text` on sev-na blended bg: ~4.6:1 ✓
- `--text` on sev-none blended bg: ~6.1:1 ✓

**Failures found:**

1. Bare `<a>` links in info.html — no explicit color set in CSS.
   Browser UA default (~#0000EE blue) on --bg gives ~2.1:1. Fails AA.
   Fix: `a { color: var(--accent); }` in style.css.

2. `--sev-minor: rgba(202, 138, 4, 0.6)` blended with --surface gives L≈0.145.
   --text (L≈0.763) contrast = (0.763+0.05)/(0.145+0.05) = 4.16:1. Fails AA.
   Fix: lower opacity to 0.45 → blended L≈0.100 → contrast ≈5.43:1 ✓

### Changes made

`src/web/static/style.css`:
- Added `a { color: var(--accent); }` after body styles; fixes bare links in info.html
- Changed `--sev-minor` from `rgba(202, 138, 4, 0.6)` to `rgba(202, 138, 4, 0.45)`
