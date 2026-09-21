import { useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import "./AppShell.css";

interface AppShellProps {
  children: ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="atlas-shell">
      <Sidebar open={sidebarOpen} onNavigate={() => setSidebarOpen(false)} />

      <div className="atlas-shell__body">
        <TopBar onMenuClick={() => setSidebarOpen((prev) => !prev)} />
        <main className="atlas-shell__content">{children}</main>
      </div>
    </div>
  );
}
