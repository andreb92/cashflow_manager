import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { lazy, Suspense, type ReactElement } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useCurrentUser } from './hooks/useCurrentUser';
import { onboardingApi } from './api/onboarding';

const AppShell = lazy(() => import('./components/layout/AppShell'));
const LoginPage = lazy(() => import('./pages/LoginPage'));
const RegisterPage = lazy(() => import('./pages/RegisterPage'));
const SetupPage = lazy(() => import('./pages/SetupPage'));
const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const TransactionsPage = lazy(() => import('./pages/TransactionsPage'));
const SummaryPage = lazy(() => import('./pages/SummaryPage'));
const TransfersPage = lazy(() => import('./pages/TransfersPage'));
const AssetsPage = lazy(() => import('./pages/AssetsPage'));
const SalaryPage = lazy(() => import('./pages/SalaryPage'));
const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'));
const ForecastingPage = lazy(() => import('./pages/ForecastingPage'));
const ForecastDetailPage = lazy(() => import('./pages/ForecastDetailPage'));
const SettingsPage = lazy(() => import('./pages/settings/SettingsPage'));
const PaymentMethodsSettings = lazy(() => import('./pages/settings/PaymentMethodsSettings'));
const CategoriesSettings = lazy(() => import('./pages/settings/CategoriesSettings'));
const TaxConfigSettings = lazy(() => import('./pages/settings/TaxConfigSettings'));
const AccountSettings = lazy(() => import('./pages/settings/AccountSettings'));

function lazyElement(node: ReactElement) {
  return <Suspense fallback={null}>{node}</Suspense>;
}

function AuthGuard() {
  const { data: user, isLoading } = useCurrentUser();
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: onboardingApi.status,
    enabled: !!user,
    retry: false,
    staleTime: 30_000,
  });

  if (isLoading || (user && statusLoading)) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (status && !status.complete) return <Navigate to="/setup" replace />;
  return <Outlet />;
}

function SetupGuard() {
  const { data: user, isLoading } = useCurrentUser();
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['onboarding', 'status'],
    queryFn: onboardingApi.status,
    enabled: !!user,
    retry: false,
    staleTime: 30_000,
  });

  if (isLoading || (user && statusLoading)) return null;
  if (user && status?.complete) return <Navigate to="/" replace />;
  return <Outlet />;
}

export function createRouter() {
  return createBrowserRouter([
  { path: '/login', element: lazyElement(<LoginPage />) },
  { path: '/register', element: lazyElement(<RegisterPage />) },
  {
    element: <SetupGuard />,
    children: [{ path: '/setup', element: lazyElement(<SetupPage />) }],
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: lazyElement(<AppShell />),
        children: [
          { path: '/', element: lazyElement(<DashboardPage />) },
          { path: '/transactions', element: lazyElement(<TransactionsPage />) },
          { path: '/summary', element: lazyElement(<SummaryPage />) },
          { path: '/transfers', element: lazyElement(<TransfersPage />) },
          { path: '/assets', element: lazyElement(<AssetsPage />) },
          { path: '/salary', element: lazyElement(<SalaryPage />) },
          { path: '/analytics', element: lazyElement(<AnalyticsPage />) },
          { path: '/forecasting', element: lazyElement(<ForecastingPage />) },
          { path: '/forecasting/:id', element: lazyElement(<ForecastDetailPage />) },
          {
            path: '/settings',
            element: lazyElement(<SettingsPage />),
            children: [
              { index: true, element: <Navigate to="payment-methods" replace /> },
              { path: 'payment-methods', element: lazyElement(<PaymentMethodsSettings />) },
              { path: 'categories', element: lazyElement(<CategoriesSettings />) },
              { path: 'tax-config', element: lazyElement(<TaxConfigSettings />) },
              { path: 'account', element: lazyElement(<AccountSettings />) },
            ],
          },
        ],
      },
    ],
  },
]);
}
