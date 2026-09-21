# Atlas v0.7 — Sprint 7 Release Notes

## Summary
Sprint 7 delivers the Atlas web application: a React + TypeScript + Vite
frontend covering all seven Intelligence Hubs, wired end-to-end to the
Sprint 6 API layer. Every displayed value traces to a real backend
response — no fabricated metrics, benchmarks, targets, or trends anywhere
in the frontend. This release also includes a frontend-wide cleanup pass
(shared component/formatter consolidation, route-level code splitting)
before Sprint 8 deployment work begins.

## Hub Routes (7/7)
`/executive` · `/revenue` · `/growth` · `/customer` · `/product` ·
`/operations` · `/market` (`/` redirects to `/executive`)

Narrative intelligence (executive briefing, insights, recommendations,
risk & alerts) is integrated through the Executive Command Center's
Narrative & Insights and Risk & Alerts sections rather than as a separate
route, matching how the backend exposes it (`/narrative/*` endpoints
consumed only by the Executive page).

## Architecture
- **API client**: single `apiGet<T>()` wrapper (`src/api/client.ts`)
  unwrapping the backend's `{data, meta, errors}` envelope, preserving
  genuine `null` values rather than coercing them
- **Resource hooks**: one `use<Resource>()` hook per endpoint, all built
  on a shared `useApiResource()` (loading/error/data), no query library
  — evaluated and deliberately deferred until enough hooks exist to
  justify the dependency
- **Shared components** (`src/components/common/`): `SectionCard`,
  `KpiSlot`, `StructuralPlaceholder`, `AnomalyCard` — used across all
  seven hubs; relocated here from `components/executive/` during the
  Sprint 7 cleanup once their cross-hub use was established, not
  speculatively upfront
- **Shared formatters** (`src/lib/formatters.ts`): currency (GBP),
  counts, percentages (whole-percent and fraction-based variants),
  signed percentages, precision variants (2-decimal, for fields the
  backend itself rounds to 2 decimals — e.g. Operations' fraud rate,
  Market's country-growth figures), ratios (multiplier and plain-decimal
  variants), hours, and 1–5 scores. Two formatters
  (`formatPercent`/`formatSignedPercent`) remain in
  `pages/executiveFormatters.ts` since they're genuinely Executive-only —
  the one backend module that returns fraction-scaled percent values
  instead of whole-percent
- **Charts**: Recharts throughout — line, bar, composed (actual + forecast
  + confidence band), and one native funnel chart. Chart colors are
  literal hex values mirroring `src/styles/tokens.css` rather than CSS
  custom properties, since Recharts renders them as raw SVG presentation
  attributes that don't reliably resolve `var(--*)` across browsers
- **Route-level code splitting**: all seven hub pages load via
  `React.lazy()` + a shared `Suspense` boundary in `App.tsx`

## Data Integrity Principles Applied Throughout
- Every proxy metric is labeled as a proxy in the UI text itself (e.g.
  Market Efficiency: "LTV/CAC exposed... not an officially defined Market
  Efficiency KPI")
- Genuine backend `null` is always rendered as an explicit unavailable
  state, never coerced to zero or hidden (MoM deltas with no prior
  period, Market's three-way country-growth distinction: real decline vs.
  exactly -100% from a positive prior vs. no comparable prior at all)
- Backend-documented "not computable" conditions (e.g. CAC/LTV-CAC with 0
  converted customers) are distinguished from genuine zero values
  wherever the response provides the data needed to tell them apart
- Backend notes, caveats, and real (not invented) benchmark text are
  surfaced verbatim in the UI rather than paraphrased into a stronger
  claim than the backend makes

## Genuine Issues Found and Fixed During Implementation
- **Currency unit bug**: the shared currency formatter was hardcoded to
  USD; every revenue-related backend field is actually GBP
  (`unit="gbp"`). Fixed once, correcting both Revenue's and Executive's
  displays simultaneously
- **Fraud-rate precision**: Operations' `fraud_rate()` rounds to 4
  decimals (not 2, like its sibling KPIs) because fraud rates are
  typically well under 1%; the default 1-decimal formatter would have
  collapsed real non-zero rates to "0.0%". Added a precision-matched
  formatter, used only where the backend's own rounding justifies it
- **Market country-growth precision**: same class of fix, applied to
  `geographic_revenue_contribution_pct` and
  `country_customer_growth_rate_mom` (both backend-rounded to 2 decimals)

## Bundle Size / Code Splitting
Before code splitting: one ~727 KB JS bundle, triggering Vite's
chunk-size warning. After route-level `React.lazy()`: chunk-size warning
is gone; largest single chunk is Recharts' shared `CartesianChart`
internals at ~338 KB. Initial load for the default `/executive` route
(which uses no charts) dropped to ~280 KB. This is an approximate,
build-tool-reported figure, not a measured real-world network metric —
no browser-based load testing was performed.

## Testing
No new automated frontend tests were added in Sprint 7. Verification was
`npm run build` (TypeScript compile + Vite bundle) and `npm run lint`
(oxlint) after every milestone, plus manual route-availability checks via
`vite preview` and static bundle-content inspection (grepping compiled
output for expected strings). **No live backend/database was available
in the implementation environment**, so no end-to-end request against a
running API was ever performed or claimed — see Known Limitations.

## Known Limitations
- **No live-data verification.** Every milestone's "verification" was
  build/lint/static-content-only. The actual runtime behavior against a
  live Postgres + FastAPI backend has never been observed.
- **No automated frontend test suite** (unit, integration, or e2e).
- Feature Adoption (Product hub) covers 4 of ~7 real event types the
  backend can query — a presentation choice, not a capability gap; the
  endpoint supports any real event type.
- A handful of small CSS pattern duplications across hub-specific files
  (e.g. an identical two-column-grid style defined independently in three
  places) were identified during cleanup and deliberately left as-is —
  no visible inconsistency, not worth the cross-file risk for a
  cosmetics-only DRY improvement at this stage.

## Deferred Architectural Items
- Further bundle optimization (e.g. splitting Recharts sub-chunks more
  aggressively) once more hubs are chart-heavy
- Consolidating the remaining minor CSS duplication noted above
- Revisiting the "one hook per endpoint" pattern for a query library
  (TanStack Query or similar) if the hook count keeps growing
