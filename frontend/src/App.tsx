import { Suspense, lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppShell } from "./components/shell/AppShell";

// Route-level code splitting: each hub page (and its charts/analytics
// deps) only loads when its route is actually visited, instead of all
// eight hubs' code shipping in one bundle. Recharts is the single
// biggest contributor to bundle size and is only used by 6 of the 8
// hub pages, so this meaningfully reduces the initial load.
const ExecutivePage = lazy(() =>
  import("./pages/ExecutivePage").then((m) => ({ default: m.ExecutivePage })),
);
const RevenuePage = lazy(() =>
  import("./pages/RevenuePage").then((m) => ({ default: m.RevenuePage })),
);
const GrowthPage = lazy(() =>
  import("./pages/GrowthPage").then((m) => ({ default: m.GrowthPage })),
);
const CustomerPage = lazy(() =>
  import("./pages/CustomerPage").then((m) => ({ default: m.CustomerPage })),
);
const ProductPage = lazy(() =>
  import("./pages/ProductPage").then((m) => ({ default: m.ProductPage })),
);
const OperationsPage = lazy(() =>
  import("./pages/OperationsPage").then((m) => ({ default: m.OperationsPage })),
);
const MarketPage = lazy(() =>
  import("./pages/MarketPage").then((m) => ({ default: m.MarketPage })),
);

function RouteFallback() {
  return (
    <div style={{ padding: "24px", color: "var(--atlas-ink-faint)", fontSize: "13px" }}>
      Loading…
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Suspense fallback={<RouteFallback />}>
          <Routes>
            <Route path="/" element={<Navigate to="/executive" replace />} />
            <Route path="/executive" element={<ExecutivePage />} />
            <Route path="/revenue" element={<RevenuePage />} />
            <Route path="/growth" element={<GrowthPage />} />
            <Route path="/customer" element={<CustomerPage />} />
            <Route path="/product" element={<ProductPage />} />
            <Route path="/operations" element={<OperationsPage />} />
            <Route path="/market" element={<MarketPage />} />
          </Routes>
        </Suspense>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
