import type { FunnelStageConversionRates } from "../../api/hubs/growth";
import { formatPercentPoints } from "../../lib/formatters";
import "./FunnelConversionRates.css";

const RATE_LABELS: Record<keyof FunnelStageConversionRates, string> = {
  registration_to_kyc_started: "Registration → KYC Started",
  kyc_started_to_approved: "KYC Started → Approved",
  kyc_approved_to_activated: "KYC Approved → Activated",
  activated_to_first_transaction: "Activated → First Transaction",
  free_to_premium: "Free → Premium",
};

export function FunnelConversionRates({
  rates,
}: {
  rates: FunnelStageConversionRates;
}) {
  return (
    <dl className="atlas-funnel-rates">
      {(Object.keys(RATE_LABELS) as (keyof FunnelStageConversionRates)[]).map((key) => (
        <div className="atlas-funnel-rates__row" key={key}>
          <dt>{RATE_LABELS[key]}</dt>
          <dd>{formatPercentPoints(rates[key])}</dd>
        </div>
      ))}
    </dl>
  );
}
