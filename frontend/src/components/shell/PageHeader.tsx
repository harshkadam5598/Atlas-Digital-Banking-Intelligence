import type { ReactNode } from "react";
import "./PageHeader.css";

interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="atlas-page-header">
      <div>
        <h1 className="atlas-page-header__title">{title}</h1>
        {description && (
          <p className="atlas-page-header__description">{description}</p>
        )}
      </div>
      {actions && <div className="atlas-page-header__actions">{actions}</div>}
    </div>
  );
}
