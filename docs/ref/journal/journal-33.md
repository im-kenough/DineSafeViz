# Journal 33

## 2026-05-07 — Fix archive year quarters flyout showing horizontally

### Problem
When hovering over a year in the Archive sub-menu, only Q1 was visible; Q2–Q4 were covered up.

### Root cause
The quarters flyout (`flex-direction: column`) stacks Q1–Q4 downward from the hovered year row.
The other year rows in the archive flyout are `position: relative` siblings that come *later* in
the DOM, so they paint on top of the quarters flyout in CSS stacking order. Only Q1 (aligned with
the hovered year's Y) was above them; Q2–Q4 fell behind subsequent year rows.

### Fix
Added to `style.css`:

```css
.flyout .dropdown-year .flyout { flex-direction: row; }
```

This targets only the third-level flyout (archive flyout → year item → quarters flyout), making
Q1–Q4 display side-by-side at the same Y as the hovered year, so they're never occluded.

### Files changed
- `src/web/static/style.css` — one rule added after `.flyout a { display: block; }`
