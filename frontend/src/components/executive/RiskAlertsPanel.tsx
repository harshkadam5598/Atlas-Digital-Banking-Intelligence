import { useRiskSummary } from "../../hooks/useRiskSummary";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { AnomalyCard } from "../common/AnomalyCard";
import { InsightCard } from "./InsightCard";
import { RecommendationCard } from "./RecommendationCard";
import "./RiskAlertsPanel.css";

export function RiskAlertsPanel() {
  const { data, isLoading, error } = useRiskSummary();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading risk summary…" />;
  }

  if (error) {
    return (
      <StructuralPlaceholder message="Unable to load the risk summary from the API." />
    );
  }

  if (!data) {
    return <StructuralPlaceholder message="No risk summary data was returned." />;
  }

  const hasAnomalies = data.anomalies.length > 0;
  const hasRiskInsights = data.risk_insights.length > 0;
  const hasRiskRecommendations = data.risk_recommendations.length > 0;
  const nothingToReport = !hasAnomalies && !hasRiskInsights && !hasRiskRecommendations;

  if (nothingToReport) {
    return (
      <p className="atlas-risk-panel__empty">
        No active risk alerts, anomalies, or risk-related recommendations.
      </p>
    );
  }

  return (
    <div className="atlas-risk-panel">
      <div className="atlas-risk-panel__summary">
        <span>{data.anomaly_count} anomalies</span>
        <span className="atlas-risk-panel__dot">·</span>
        <span>{data.risk_insight_count} risk insights</span>
        <span className="atlas-risk-panel__dot">·</span>
        <span>{data.risk_recommendation_count} recommendations</span>
      </div>

      {hasAnomalies && (
        <div className="atlas-risk-panel__section">
          <h3 className="atlas-risk-panel__heading">Anomalies</h3>
          {data.anomalies.map((anomaly, i) => (
            <AnomalyCard key={`${anomaly.metric}-${anomaly.detected_at}-${i}`} anomaly={anomaly} />
          ))}
        </div>
      )}

      {hasRiskInsights && (
        <div className="atlas-risk-panel__section">
          <h3 className="atlas-risk-panel__heading">Risk Insights</h3>
          {data.risk_insights.map((insight, i) => (
            <InsightCard key={`${insight.headline}-${i}`} insight={insight} />
          ))}
        </div>
      )}

      {hasRiskRecommendations && (
        <div className="atlas-risk-panel__section">
          <h3 className="atlas-risk-panel__heading">Recommendations</h3>
          {data.risk_recommendations.map((rec, i) => (
            <RecommendationCard key={`${rec.title}-${i}`} recommendation={rec} />
          ))}
        </div>
      )}
    </div>
  );
}
