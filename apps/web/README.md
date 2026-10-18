# Web application

The planned frontend stack is Next.js, React, and TypeScript. This directory
is reserved for that application; no frontend runtime, page, or functionality
is part of Phase 1.

## Manually copied assets

`public/valuation/football-field.svg` is a plain copy of
`docs/reports/valuation/football-field.svg` (not a symlink). If the source
chart changes, re-copy it:

    cp docs/reports/valuation/football-field.svg apps/web/public/valuation/football-field.svg
