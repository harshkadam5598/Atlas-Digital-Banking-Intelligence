import type { ReactNode } from "react";
import "./SectionCard.css";

interface SectionCardProps {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
}

export function SectionCard({
  title,
  description,
  children,
  actions,
}: SectionCardProps) {
  return (
    <section className="atlas-section-card">
      <header className="atlas-section-card__header">
        <div>
          <h2 className="atlas-section-card__title">{title}</h2>
          {description && (
            <p className="atlas-section-card__description">{description}</p>
          )}
        </div>
        {actions && (
          <div className="atlas-section-card__actions">{actions}</div>
        )}
      </header>
      <div className="atlas-section-card__body">{children}</div>
    </section>
  );
}
