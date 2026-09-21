import { Menu } from "lucide-react";
import "./TopBar.css";

interface TopBarProps {
  onMenuClick: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
  return (
    <header className="atlas-topbar">
      <button
        type="button"
        className="atlas-topbar__menu"
        onClick={onMenuClick}
        aria-label="Toggle navigation"
      >
        <Menu size={18} strokeWidth={1.75} />
      </button>

      <div className="atlas-topbar__spacer" />

      <div className="atlas-topbar__meta">
        <span className="atlas-topbar__meta-label">Data as of</span>
        <span className="atlas-topbar__meta-value">—</span>
      </div>

      <div className="atlas-topbar__user" aria-hidden="true">
        <span className="atlas-topbar__user-initial">H</span>
      </div>
    </header>
  );
}
