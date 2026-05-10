# Journal 7

## 2026-04-26 — Design: dark theme and CSS extraction

### Context
- Branch: `dev-app`
- Task: plan a dark theme, extract inline CSS to a static file, add severity-based row color coding

### Log

**Brainstorming session**
- Explored `src/dsv-app/templates/index.html` — all CSS is inline in a `<style>` block, no `static/` dir
- Reviewed journal-6 for current template structure
- Three approaches considered for row coloring: CSS classes (chosen), inline style=, data-attribute selector
- User approved: Approach A (CSS classes), dark municipal terminal palette, fonts unchanged
- Design spec written to `docs/superpowers/specs/2026-04-26-dark-theme-design.md`
