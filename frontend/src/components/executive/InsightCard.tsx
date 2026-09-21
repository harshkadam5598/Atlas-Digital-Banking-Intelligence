import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import type { NarrativeInsight } from "../../api/hubs/narrative";
import "./InsightCard.css";

const DIRECTION_ICON = {
  up: TrendingUp,
  down: TrendingDown,
  flat: Minus,
} as const;

export function InsightCard({ insight }: { insight: NarrativeInsight }) {
  const DirectionIcon = DIRECTION_ICON[insight.direction];
  const directionTone =
    insight.direction === "up" ? "positive" : insight.direction === "down" ? "negative" : "neutral";

  return (
    <article className="atlas-insight-card">
      <div className="atlas-insight-card__top">
        <span className={`atlas-insight-card__direction atlas-insight-card__direction--${directionTone}`}>
          <DirectionIcon size={14} strokeWidth={2} />
          {insight.magnitude_pct.toFixed(1)}%
        </span>
        {insight.is_risk && <span className="atlas-tag atlas-tag--risk">Risk</span>}
        {insight.is_opportunity && (
          <span className="atlas-tag atlas-tag--opportunity">Opportunity</span>
        )}
        <span className="atlas-tag atlas-tag--neutral">{insight.category}</span>
        <span className="atlas-insight-card__confidence">
          {insight.confidence} confidence
        </span>
      </div>
      <p className="atlas-insight-card__headline">{insight.headline}</p>
      <p className="atlas-insight-card__driver">{insight.primary_driver}</p>
    </article>
  );
}
