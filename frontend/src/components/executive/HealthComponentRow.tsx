import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import "./HealthComponentRow.css";

interface HealthComponentRowProps {
  label: string;
  weightLabel: string;
  /** 0–100 fill for bounded metrics (e.g. retention). Omit for signed/unbounded metrics. */
  barPercent?: number;
  /** Formatted signed value for growth-style metrics (e.g. "+4.2%"). */
  signedValue?: string;
  isPositive?: boolean;
  /** Present (non-null) only when the backend has no value for this component. */
  unavailableReason?: string;
}

export function HealthComponentRow({
  label,
  weightLabel,
  barPercent,
  signedValue,
  isPositive,
  unavailableReason,
}: HealthComponentRowProps) {
  return (
    <div className="atlas-health-row">
      <div className="atlas-health-row__meta">
        <span className="atlas-health-row__label">{label}</span>
        <span className="atlas-health-row__weight">{weightLabel}</span>
      </div>

      {unavailableReason ? (
        <div className="atlas-health-row__unavailable">
          <span className="atlas-health-row__unavailable-value">—</span>
          <span className="atlas-health-row__unavailable-reason">
            {unavailableReason}
          </span>
        </div>
      ) : barPercent !== undefined ? (
        <div className="atlas-health-row__bar-wrap">
          <div className="atlas-health-row__bar-track">
            <div
              className="atlas-health-row__bar-fill"
              style={{ width: `${Math.min(Math.max(barPercent, 0), 100)}%` }}
            />
          </div>
          <span className="atlas-health-row__bar-value">
            {barPercent.toFixed(1)}%
          </span>
        </div>
      ) : (
        <div className="atlas-health-row__signed">
          {isPositive ? (
            <ArrowUpRight size={15} className="atlas-health-row__icon--positive" />
          ) : (
            <ArrowDownRight size={15} className="atlas-health-row__icon--negative" />
          )}
          <span
            className={
              isPositive
                ? "atlas-health-row__signed-value atlas-health-row__signed-value--positive"
                : "atlas-health-row__signed-value atlas-health-row__signed-value--negative"
            }
          >
            {signedValue}
          </span>
        </div>
      )}
    </div>
  );
}
