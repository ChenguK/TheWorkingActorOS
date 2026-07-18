import { Component, Suspense, lazy, type ErrorInfo, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { TopNavigation } from "./layout/TopNavigation";
import { useSystemCapabilities } from "./services/system";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const AuditionsPage = lazy(() => import("./pages/AuditionsPage").then((module) => ({ default: module.AuditionsPage })));
const OpportunitiesPage = lazy(() => import("./pages/OpportunitiesPage").then((module) => ({ default: module.OpportunitiesPage })));
const MaterialsPage = lazy(() => import("./pages/MaterialsPage").then((module) => ({ default: module.MaterialsPage })));
const CareerPage = lazy(() => import("./pages/CareerPage").then((module) => ({ default: module.CareerPage })));
const AnalyticsPage = lazy(() => import("./pages/AnalyticsPage").then((module) => ({ default: module.AnalyticsPage })));
const RelationshipsPage = lazy(() => import("./pages/RelationshipsPage").then((module) => ({ default: module.RelationshipsPage })));
const CalendarPage = lazy(() => import("./pages/CalendarPage").then((module) => ({ default: module.CalendarPage })));
const JournalPage = lazy(() => import("./pages/JournalPage").then((module) => ({ default: module.JournalPage })));
const ProfilePage = lazy(() => import("./pages/ProfilePage").then((module) => ({ default: module.ProfilePage })));
const ProfileSetupPage = lazy(() => import("./pages/ProfileSetupPage").then((module) => ({ default: module.ProfileSetupPage })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then((module) => ({ default: module.SettingsPage })));

function RouteLoading() {
  return (
    <div
      className="rounded-lg border border-slate-200 bg-white px-4 py-6 text-sm text-slate-600 shadow-sm"
      role="status"
      aria-live="polite"
    >
      Loading workspace section...
    </div>
  );
}

class RouteErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null };

  static getDerivedStateFromError(error: Error) {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Route failed to load", error, errorInfo);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
          This workspace section could not load. Refresh the page and try again.
        </div>
      );
    }
    return this.props.children;
  }
}

function App() {
  const capabilities = useSystemCapabilities();

  return (
    <main className="min-h-screen">
      <TopNavigation capabilities={capabilities.data ?? null} />
      <div className="actor-workspace mx-auto grid max-w-7xl gap-4 px-4 py-5">
        <RouteErrorBoundary>
          <Suspense fallback={<RouteLoading />}>
            <Routes>
              <Route path="/" element={<DashboardPage />} />
              <Route path="/auditions" element={<AuditionsPage />} />
              <Route path="/breakdowns" element={<OpportunitiesPage />} />
              <Route path="/discovery" element={<Navigate to="/breakdowns" replace />} />
              <Route path="/opportunities" element={<Navigate to="/breakdowns" replace />} />
              <Route path="/materials" element={<MaterialsPage />} />
              <Route path="/career" element={<CareerPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
              <Route path="/relationships" element={<RelationshipsPage />} />
              <Route path="/calendar" element={<CalendarPage />} />
              <Route path="/journal" element={<JournalPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/profile/setup" element={<ProfileSetupPage />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </RouteErrorBoundary>
      </div>
    </main>
  );
}

export default App;
