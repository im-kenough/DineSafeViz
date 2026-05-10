# Journal 16

## 2026-04-28 — Uniform button styling + 25% size increase

### Context
Branch: `task-ui-btn-uniform`
Task: Make all buttons look like the GitHub/LinkedIn social buttons, then scale up 25%.

### Files reviewed
- `src/dsv-app/static/style.css` — tab, social-links, flyout, dropdown styles
- `src/dsv-app/templates/index.html`, `dashboard.html`, `info.html` — button markup

### Analysis
Two distinct button styles existed:
1. **Tab buttons** (`.tabs > a`): gray `var(--border)` border, no font-weight, fixed `flex: 0 0 9rem`, `padding: 0.4rem 1rem`
2. **Social buttons** (`.social-links a`): accent `var(--accent)` border, `font-weight: 600`, `font-size: 0.875rem`, `padding: 0.4rem 0.85rem`, auto-sized
3. **Flyout links** (`.flyout a`): gray border, no weight

### Decision
Reference style = social buttons (GitHub/LinkedIn). Unify all to that style, then scale 25%.

Final values after 25% increase:
- `padding: 0.5rem 1.0625rem` (0.4 × 1.25 / 0.85 × 1.25)
- `font-size: 1.094rem` (0.875 × 1.25)
- SVG icons: `20×20` (16 × 1.25)
- gap: `0.5rem` (0.4 × 1.25)
- Active/hover: filled `var(--accent)` background

### Changes made
- `src/dsv-app/static/style.css`: unified all button CSS rules, removed fixed `flex: 0 0 9rem`
- `src/dsv-app/templates/index.html`: SVG 16→20 on LinkedIn and GitHub icons
- `src/dsv-app/templates/dashboard.html`: same SVG update
- `src/dsv-app/templates/info.html`: same SVG update
