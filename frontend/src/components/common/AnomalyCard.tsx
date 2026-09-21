import type { Anomaly } from "../../api/sharedTypes";
import { formatMetricValue, formatSignedPercentPoints } from "../../lib/formatters";
import "./AnomalyCard.css";

const SEVERITY_CLASS = {
  critical: "atlas-tag--severity-critical",
  high: "atlas-tag--severity-high",
  medium: "atlas-tag--severity-medium",
  low: "atlas-tag--severity-low",
} as const;

export function AnomalyCard({ anomaly }: { anomaly: Anomaly }) {
  return (
    <article className="atlas-anomaly-card">
      <div className="atlas-anomaly-card__top">
        <span className={`atlas-tag ${SEVERITY_CLASS[anomaly.severity]}`}>
          {anomaly.severity}
        </span>
        <span className="atlas-tag atlas-tag--neutral">{anomaly.metric}</span>
        {anomaly.dimension && (
          <span className="atlas-tag atlas-tag--neutral">{anomaly.dimension}</span>
        )}
        <span className="atlas-anomaly-card__deviation">
          {formatSignedPercentPoints(anomaly.deviation_pct)} vs. expected
        </span>
      </div>

      <p className="atlas-anomaly-card__reason">{anomaly.detection_reason}</p>

      <div className="atlas-anomaly-card__values">
        <span>
          Observed <strong>{formatMetricValue(anomaly.observed_value)}</strong>
        </span>
        <span>
          Expected <strong>{formatMetricValue(anomaly.expected_value)}</strong>
        </span>
        <span className="atlas-anomaly-card__date">
          Detected {anomaly.detected_at}
        </span>
      </div>

      <p className="atlas-anomaly-card__impact">{anomaly.business_impact}</p>
      <p className="atlas-anomaly-card__investigation">
        Suggested investigation: {anomaly.suggested_investigation}
      </p>
    </article>
  );
}
