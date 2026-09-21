/**
 * Executive-only formatters.
 *
 * Split out during the Sprint 7-wide cleanup: these two are the only
 * formatters that are genuinely specific to one hub. executive_service.py
 * is the one backend module that returns percent-unit fields as
 * fractions (e.g. 0.0203 = 2.03%) rather than whole-percent numbers —
 * every other hub's percent fields use lib/formatters.ts's
 * formatPercentPoints instead. Everything else previously in this file
 * moved to src/lib/formatters.ts unchanged.
 */

/** Backend sends growth/rate fields as fractions (e.g. 0.0203 = 2.03%). */
export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/** Same as formatPercent but with an explicit + sign for non-negative values. */
export function formatSignedPercent(value: number): string {
  const pct = value * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
}
