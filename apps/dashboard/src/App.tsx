import { Navigate, Route, Routes } from "react-router-dom";
import { AuthGate } from "./components/AuthGate";
import { Layout } from "./components/Layout";
import { FindingsPage } from "./pages/Findings";
import { OverviewPage } from "./pages/Overview";
import { PullRequestDetailPage } from "./pages/PullRequestDetail";
import { PullRequestsPage } from "./pages/PullRequests";
import { RepositoriesPage } from "./pages/Repositories";
import { SettingsPage } from "./pages/Settings";
import { TrendsPage } from "./pages/Trends";

export default function App() {
  return (
    <AuthGate>
      {(username) => (
        <Layout username={username}>
          <Routes>
            <Route path="/" element={<OverviewPage />} />
            <Route path="/pull-requests" element={<PullRequestsPage />} />
            <Route path="/pull-requests/:owner/:repo/:number" element={<PullRequestDetailPage />} />
            <Route path="/findings" element={<FindingsPage />} />
            <Route path="/repositories" element={<RepositoriesPage />} />
            <Route path="/trends" element={<TrendsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Layout>
      )}
    </AuthGate>
  );
}
