import type { NarrativeRecommendation } from "../../api/hubs/narrative";
import "./RecommendationCard.css";

const PRIORITY_CLASS = {
  High: "atlas-tag--priority-high",
  Medium: "atlas-tag--priority-medium",
  Low: "atlas-tag--priority-low",
} as const;

export function RecommendationCard({
  recommendation,
}: {
  recommendation: NarrativeRecommendation;
}) {
  return (
    <article className="atlas-recommendation-card">
      <div className="atlas-recommendation-card__top">
        <span className={`atlas-tag ${PRIORITY_CLASS[recommendation.priority]}`}>
          {recommendation.priority} priority
        </span>
        <span className="atlas-tag atlas-tag--neutral">{recommendation.category}</span>
      </div>
      <p className="atlas-recommendation-card__title">{recommendation.title}</p>
      <p className="atlas-recommendation-card__rationale">{recommendation.rationale}</p>
      <p className="atlas-recommendation-card__impact">
        Estimated impact: {recommendation.estimated_impact}
      </p>
    </article>
  );
}
