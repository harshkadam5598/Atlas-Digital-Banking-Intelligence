import "./KpiSlot.css";

interface KpiSlotProps {
  label: string;
  /** Formatted display value, or null when there's nothing to show yet. */
  value: string | null;
  caption: string;
  tone?: "default" | "error";
}

/**
 * Renders one KPI. `value === null` always means "nothing to display" —
 * loading, an unreachable API, or a genuine backend null (e.g. a KPI
 * with no backing implementation) — never a fabricated number. The
 * `caption` is what tells those three apart to the person reading it.
 */
export function KpiSlot({ label, value, caption, tone = "default" }: KpiSlotProps) {
  return (
    <div className="atlas-kpi-slot">
      <span className="atlas-kpi-slot__label">{label}</span>
      <span
        className={`atlas-kpi-slot__value ${
          value === null ? "atlas-kpi-slot__value--empty" : ""
        }`}
      >
        {value ?? "—"}
      </span>
      <span
        className={`atlas-kpi-slot__status ${
          tone === "error" ? "atlas-kpi-slot__status--error" : ""
        }`}
      >
        {caption}
      </span>
    </div>
  );
}
