import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './pages/LoginPage';
import { RepositoriesPage } from './pages/RepositoriesPage';
import { RepositoryDetailPage } from './pages/RepositoryDetailPage';
import { PullRequestsPage } from './pages/PullRequestsPage';
import { PRDetailPage } from './pages/PRDetailPage';
import { ReviewQueuePage } from './pages/ReviewQueuePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Login — standalone, no app layout */}
        <Route path="/login" element={<LoginPage />} />

        {/* App routes — wrapped in AppLayout (Navbar + footer) */}
        <Route element={<AppLayout />}>
          {/* Repositories list */}
          <Route path="/repositories" element={<RepositoriesPage />} />

          {/* Stage 6: Repository detail — Overview / Security / Commits tabs */}
          <Route path="/repositories/:repoId" element={<RepositoryDetailPage />} />

          {/* Repository pull requests list */}
          <Route path="/repositories/:repoId/pull-requests" element={<PullRequestsPage />} />

          {/* PR detail / review cockpit */}
          <Route path="/pull-requests/:id" element={<PRDetailPage />} />

          {/* Review queue dashboard */}
          <Route path="/review-queue" element={<ReviewQueuePage />} />
        </Route>

        {/* Root redirect */}
        <Route path="/" element={<Navigate to="/repositories" replace />} />

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/repositories" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
