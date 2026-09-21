import { useBriefing } from "../../hooks/useBriefing";
import { StructuralPlaceholder } from "../common/StructuralPlaceholder";
import { InsightCard } from "./InsightCard";
import { RecommendationCard } from "./RecommendationCard";
import "./NarrativePanel.css";

export function NarrativePanel() {
  const { data, isLoading, error } = useBriefing();

  if (isLoading) {
    return <StructuralPlaceholder message="Loading executive briefing…" />;
  }

  if (error) {
    return (
      <StructuralPlaceholder message="Unable to load the narrative briefing from the API." />
    );
  }

  if (!data) {
    return <StructuralPlaceholder message="No briefing data was returned." />;
  }

  const hasInsights = data.top_insights.length > 0;
  const hasRecommendations = data.top_recommendations.length > 0;

  return (
    <div className="atlas-narrative-panel">
      <div className="atlas-narrative-panel__summary">
        <span>{data.insight_count} insights</span>
        <span className="atlas-narrative-panel__dot">·</span>
        <span>{data.risk_count} risk</span>
        <span className="atlas-narrative-panel__dot">·</span>
        <span>{data.opportunity_count} opportunity</span>
        <span className="atlas-narrative-panel__dot">·</span>
        <span>{data.recommendation_count} recommendations</span>
      </div>

      <div className="atlas-narrative-panel__section">
        <h3 className="atlas-narrative-panel__heading">Insights</h3>
        {hasInsights ? (
          data.top_insights.map((insight, i) => (
            <InsightCard key={`${insight.headline}-${i}`} insight={insight} />
          ))
        ) : (
          <p className="atlas-narrative-panel__empty">
            No insights available for this period.
          </p>
        )}
      </div>

      <div className="atlas-narrative-panel__section">
        <h3 className="atlas-narrative-panel__heading">Recommendations</h3>
        {hasRecommendations ? (
          data.top_recommendations.map((rec, i) => (
            <RecommendationCard key={`${rec.title}-${i}`} recommendation={rec} />
          ))
        ) : (
          <p className="atlas-narrative-panel__empty">
            No recommendations available for this period.
          </p>
        )}
      </div>
    </div>
  );
}
