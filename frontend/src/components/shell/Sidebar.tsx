import { NavLink } from "react-router-dom";
import {
  LayoutGrid,
  LineChart,
  TrendingUp,
  Users,
  Boxes,
  Settings2,
  Globe2,
} from "lucide-react";
import "./Sidebar.css";

interface NavItem {
  label: string;
  to: string;
  icon: React.ComponentType<{ size?: number; strokeWidth?: number }>;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Executive", to: "/executive", icon: LayoutGrid },
  { label: "Revenue", to: "/revenue", icon: LineChart },
  { label: "Growth", to: "/growth", icon: TrendingUp },
  { label: "Customer", to: "/customer", icon: Users },
  { label: "Product", to: "/product", icon: Boxes },
  { label: "Operations", to: "/operations", icon: Settings2 },
  { label: "Market", to: "/market", icon: Globe2 },
];

interface SidebarProps {
  open: boolean;
  onNavigate: () => void;
}

export function Sidebar({ open, onNavigate }: SidebarProps) {
  return (
    <>
      <aside className={`atlas-sidebar ${open ? "atlas-sidebar--open" : ""}`}>
        <div className="atlas-sidebar__brand">
          <span className="atlas-sidebar__brand-mark">A</span>
          <span className="atlas-sidebar__brand-name">Atlas</span>
        </div>

        <nav className="atlas-sidebar__nav" aria-label="Intelligence hubs">
          {NAV_ITEMS.map(({ label, to, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={onNavigate}
              className={({ isActive }) =>
                `atlas-sidebar__link ${isActive ? "atlas-sidebar__link--active" : ""}`
              }
            >
              <Icon size={17} strokeWidth={1.75} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="atlas-sidebar__footer">
          <span className="atlas-sidebar__footer-label">Environment</span>
          <span className="atlas-sidebar__footer-value">Development</span>
        </div>
      </aside>

      {open && (
        <button
          type="button"
          className="atlas-sidebar__scrim"
          aria-label="Close navigation"
          onClick={onNavigate}
        />
      )}
    </>
  );
}
