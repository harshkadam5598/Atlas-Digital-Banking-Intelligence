import { useHealthScore } from "../../hooks/useHealthScore";
import { HealthComponentRow } from "./HealthComponentRow";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { formatSignedPercent } from "../../pages/executiveFormatters";
import "./HealthScoreBreakdown.css";

/**
 * The Executive hub has no time-series/trend endpoint — /health-score
 * returns a single as-of snapshot, and score/rating are always null
 * (no composite scoring implemented on the backend yet). So this
 * renders the real component breakdown rather than a fabricated trend
 * line. See the Sprint 7 milestone report for the full reasoning.
 */
export function HealthScoreBreakdown() {
  const { data, isLoading, error } = useHealthScore();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading health score components…" />;
  }

  if (error) {
    return (
      <StructuralPlaceholder message="Unable to load health score data from the API." />
    );
  }

  if (!data) {
    return <StructuralPlaceholder message="No health score data was returned." />;
  }

  const { components, unavailable_fields, as_of_date, formula } = data;

  return (
    <div className="atlas-health-breakdown">
      <div className="atlas-health-breakdown__rows">
        <HealthComponentRow
          label="30-Day Retention"
          weightLabel="25% weight"
          barPercent={components.retention_30d * 100}
        />
        <HealthComponentRow
          label="Revenue Growth (MoM)"
          weightLabel="20% weight"
          signedValue={formatSignedPercent(components.revenue_growth_mom)}
          isPositive={components.revenue_growth_mom >= 0}
        />
        <HealthComponentRow
          label="Activation Rate"
          weightLabel="25% weight"
          unavailableReason={unavailable_fields.activation_rate}
        />
        <HealthComponentRow
          label="NPS Proxy"
          weightLabel="15% weight"
          unavailableReason={unavailable_fields.nps_proxy}
        />
        <HealthComponentRow
          label="Operational Uptime"
          weightLabel="15% weight"
          unavailableReason={unavailable_fields.operational_uptime}
        />
      </div>

      <div className="atlas-health-breakdown__footnote">
        <span>As of {as_of_date}</span>
        <span className="atlas-health-breakdown__divider">·</span>
        <span>
          Composite score unavailable — 3 of 5 weighted components have no
          backing implementation
        </span>
      </div>
      <p className="atlas-health-breakdown__formula">{formula}</p>
    </div>
  );
}
