import { createBrowserRouter, Navigate, Outlet } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useCurrentUser } from './hooks/useCurrentUser';
import { onboardingApi } from './api/onboarding';
import AppShell from './components/layout/AppShell';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import SetupPage from './pages/SetupPage';
import DashboardPage from './pages/DashboardPage';
import TransactionsPage from './pages/TransactionsPage';
import SummaryPage from './pages/SummaryPage';
import TransfersPage from './pages/TransfersPage';
import AssetsPage from './pages/AssetsPage';
import SalaryPage from './pages/SalaryPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ForecastingPage from './pages/ForecastingPage';
import ForecastDetailPage from './pages/ForecastDetailPage';
import SettingsPage from './pages/settings/SettingsPage';
import PaymentMethodsSettings from './pages/settings/PaymentMethodsSettings';
import CategoriesSettings from './pages/settings/CategoriesSettings';
import TaxConfigSettings from './pages/settings/TaxConfigSettings';
import AccountSettings from './pages/settings/AccountSettings';

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
  { path: '/login', element: <LoginPage /> },
  { path: '/register', element: <RegisterPage /> },
  {
    element: <SetupGuard />,
    children: [{ path: '/setup', element: <SetupPage /> }],
  },
  {
    element: <AuthGuard />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: '/', element: <DashboardPage /> },
          { path: '/transactions', element: <TransactionsPage /> },
          { path: '/summary', element: <SummaryPage /> },
          { path: '/transfers', element: <TransfersPage /> },
          { path: '/assets', element: <AssetsPage /> },
          { path: '/salary', element: <SalaryPage /> },
          { path: '/analytics', element: <AnalyticsPage /> },
          { path: '/forecasting', element: <ForecastingPage /> },
          { path: '/forecasting/:id', element: <ForecastDetailPage /> },
          {
            path: '/settings',
            element: <SettingsPage />,
            children: [
              { index: true, element: <Navigate to="payment-methods" replace /> },
              { path: 'payment-methods', element: <PaymentMethodsSettings /> },
              { path: 'categories', element: <CategoriesSettings /> },
              { path: 'tax-config', element: <TaxConfigSettings /> },
              { path: 'account', element: <AccountSettings /> },
            ],
          },
        ],
      },
    ],
  },
]);
}

