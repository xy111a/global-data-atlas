# Global Data Atlas audit — 2026-08-09

Scope: world map start, China search/drill-down, and 390 px mobile layout.

## Confirmed

- All bundled automated checks passed: syntax, data consistency, offline regression, comparison mode, and extended-indicator checks.
- The visual flow loaded without console errors after a brief initial map load.

## Findings

1. Chinese province ranking adds `省` to every item, yielding incorrect labels such as 上海省、北京省、重庆省. See `global-data-atlas.html:1300`.
2. Map and ranking are pointer-only interaction surfaces: the ECharts canvas is not keyboard focusable and ranking rows are non-focusable `div`s with click handlers. Keyboard and assistive-technology users cannot perform the primary exploration workflow. See `global-data-atlas.html:211` and `global-data-atlas.html:1312`.
3. At 390 px the action row is clipped on the right; the return control is only partly visible in the captured state. The header permits wrapping but the action group is pushed right with `margin-left:auto`, while controls retain fixed/minimum widths. See `global-data-atlas.html:62` and `global-data-atlas.html:157`.
4. User/data-derived strings are interpolated into `innerHTML` in breadcrumbs, dashboard fields, and ranking rows without escaping. Bundled data is trusted today, but dynamic geographic fallback content creates a future injection boundary. See `global-data-atlas.html:728`, `global-data-atlas.html:927`, and `global-data-atlas.html:1312`.

## Evidence

- `01-world.png`: completed world-map screen.
- `02-china.png`: China search state, showing the incorrect province suffixes in the ranking.
- `03-mobile.png`: 390 px responsive layout.
