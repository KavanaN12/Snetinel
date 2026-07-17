import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Suspense, lazy, useState } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { LoadingState } from './components/common/LoadingState';
import { NotFoundPage } from './pages/NotFoundPage';
import { useAuthStore } from './store/auth';

const LoginPage = lazy(() => import('./pages/LoginPage').then((module) => ({ default: module.LoginPage })));
const RegisterPage = lazy(() => import('./pages/RegisterPage').then((module) => ({ default: module.RegisterPage })));
const DashboardPage = lazy(() => import('./pages/DashboardPage').then((module) => ({ default: module.DashboardPage })));
const DiscoveryPage = lazy(() => import('./pages/DiscoveryPage').then((module) => ({ default: module.DiscoveryPage })));
const AttackPathsPage = lazy(() => import('./pages/AttackPathsPage').then((module) => ({ default: module.AttackPathsPage })));
const FindingsPage = lazy(() => import('./pages/FindingsPage').then((module) => ({ default: module.FindingsPage })));
const CompliancePage = lazy(() => import('./pages/CompliancePage').then((module) => ({ default: module.CompliancePage })));
const DriftPage = lazy(() => import('./pages/DriftPage').then((module) => ({ default: module.DriftPage })));
const RagPage = lazy(() => import('./pages/RagPage').then((module) => ({ default: module.RagPage })));
const AuditPage = lazy(() => import('./pages/AuditPage').then((module) => ({ default: module.AuditPage })));
const SettingsPage = lazy(() => import('./pages/SettingsPage').then((module) => ({ default: module.SettingsPage })));

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
}

function RootRoute() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/login" replace />;
}

function App() {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
    },
  }));

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <BrowserRouter>
          <Suspense fallback={<LoadingState message="Loading Sentinel…" />}>
            <Routes>
              <Route path="/" element={<RootRoute />} />
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route
                element={
                  <ProtectedRoute>
                    <AppLayout />
                  </ProtectedRoute>
                }
              >
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/discovery" element={<DiscoveryPage />} />
                <Route path="/attack-paths" element={<AttackPathsPage />} />
                <Route path="/findings" element={<FindingsPage />} />
                <Route path="/compliance" element={<CompliancePage />} />
                <Route path="/drift" element={<DriftPage />} />
                <Route path="/rag" element={<RagPage />} />
                <Route path="/audit" element={<AuditPage />} />
                <Route path="/settings" element={<SettingsPage />} />
              </Route>
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </Suspense>
        </BrowserRouter>
      </ErrorBoundary>
    </QueryClientProvider>
  );
}

export default App;
