# Journal 22

## 2026-04-28 — Add mobile and tablet responsive breakpoints

Task: support latest iPhone, Google Pixel, Samsung Galaxy, and iPad resolutions.

### Device logical widths targeted

| Device family        | CSS width (portrait) |
|----------------------|----------------------|
| Samsung Galaxy S24   | 360px                |
| Galaxy S24+/Ultra    | 412px                |
| iPhone 16 / Pro      | 390–393px            |
| iPhone 16 Plus/Max   | 430px                |
| Pixel 9 / Pro        | 412px                |
| iPad mini (6th)      | 744px                |
| iPad (10th gen)      | 820px                |
| iPad Air 11"         | 820px                |
| iPad Pro 11"         | 834px                |
| iPad Air / Pro 13"   | 1024px               |

Breakpoints chosen:
- ≤ 600px → mobile phones (all portrait phone widths are ≤ 430px)
- 601px–1023px → tablet portrait + phone landscape
- ≥ 1024px → tablet landscape + desktop (pre-existing layout works)

### Issues identified

1. `body { padding: 0 2rem }` → 64px total side padding on a 390px screen leaves only ~326px; too tight.
2. `.social-links { margin-left: auto }` causes an odd visual gap when the flex row wraps on narrow viewports.
3. Social link labels ("LinkedIn", "GitHub") add ~100px+ each; hiding them on mobile saves space while keeping the icon.
4. `dashboard-frame { height: calc(100vh - 120px) }` — when the nav wraps on mobile, the header area is taller; bumped offset to 180px on mobile.
5. No tablet-range padding rule existed (fell through to the desktop 2rem value).

### Changes made

- `base.html`: wrapped "LinkedIn" and "GitHub" text in `<span class="link-label">` so CSS can hide them on mobile.
- `style.css`: added `@media (max-width: 600px)` and `@media (601px) and (max-width: 1023px)` blocks.
- `dashboard.html`: added mobile `@media (max-width: 600px)` inside the inline `<style>` to increase iframe height offset.

### Hover-only dropdowns on touch (fixed in follow-up)

Added minimal JS inline in base.html to toggle `.is-open` class:
- "Inspections ▾" click → `e.preventDefault()`, toggle `.dropdown-menu.is-open`
- Year row click → toggle `.flyout.is-open` (unless click was on a quarter `<a>` link)
- Outside click → close all

CSS: added `.dropdown-menu.is-open` and `.flyout.is-open` alongside existing `:hover` rules so both desktop and mobile stay consistent.

Mobile flyout layout: overrode `position: absolute; left: 100%` to `position: static` inside the `≤600px` block — flyouts now stack below their year row instead of floating off-screen to the right.

Side-effect: "Inspections ▾" direct click-to-navigate is now intercepted on all devices (desktop hover still works for the menu; the link still functions as a fallback when JS is off).
