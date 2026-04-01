import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes, Outlet } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import SetupPage from '../../src/pages/SetupPage';

// SetupPage manages its own QueryClientProvider and OnboardingProvider internally,
// so the test wrapper only needs MemoryRouter.
function wrapper({ children }: { children: React.ReactNode }) {
  return <MemoryRouter>{children}</MemoryRouter>;
}

// ---------------------------------------------------------------------------
// Tests: SetupPage wizard content
// ---------------------------------------------------------------------------

test('SetupPage renders without crashing and shows wizard heading', async () => {
  render(<SetupPage />, { wrapper });
  expect(screen.getByText('Setup your account')).toBeInTheDocument();
});

test('SetupPage step 1 shows start-date heading', async () => {
  render(<SetupPage />, { wrapper });
  expect(screen.getByText('When do you want to start tracking?')).toBeInTheDocument();
});

test('SetupPage step 1 shows step indicator "Step 1 of 8"', async () => {
  render(<SetupPage />, { wrapper });
  expect(screen.getByText('Step 1 of 8')).toBeInTheDocument();
});

test('SetupPage step 1 has a Next button', async () => {
  render(<SetupPage />, { wrapper });
  expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
});

test('SetupPage advances to step 2 after filling start date and clicking Next', async () => {
  const user = userEvent.setup();
  render(<SetupPage />, { wrapper });

  // Fill the required date field on step 1
  const dateInput = screen.getByLabelText(/tracking start date/i);
  await user.type(dateInput, '2026-01-01');

  await user.click(screen.getByRole('button', { name: /next/i }));

  // Step 2 heading
  await waitFor(() =>
    expect(screen.getByText('Main bank account')).toBeInTheDocument()
  );
  expect(screen.getByText('Step 2 of 8')).toBeInTheDocument();
});

// ---------------------------------------------------------------------------
// Tests: SetupGuard redirect for already-onboarded users
// ---------------------------------------------------------------------------

// SetupGuard is not exported directly; we reproduce its behaviour by rendering
// the guarded route tree with MemoryRouter starting at /setup.
// When onboarding is complete the guard redirects to /, so we assert that
// the home placeholder renders instead of the setup wizard.

// Import the guard from the router module so we don't duplicate logic.
// The router module exports createRouter but not SetupGuard individually.
// Instead we inline a thin reproduction that mirrors the real guard exactly.
import { useQuery } from '@tanstack/react-query';
import { Navigate } from 'react-router-dom';
import { onboardingApi } from '../../src/api/onboarding';
import { fetchMeOrNull } from '../../src/api/auth';

function TestSetupGuard() {
  const { data: user, isLoading } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: fetchMeOrNull,
    retry: false,
    staleTime: 30_000,
  });
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

function guardWrapper({ children: _children }: { children: React.ReactNode }) {
  // We build the route tree ourselves here so this wrapper is unused,
  // but the render helper still expects it.
  return <>{_children}</>;
}

test('SetupGuard redirects to "/" when onboarding is already complete', async () => {
  // Override the default handler so onboarding is complete
  server.use(
    http.get('/api/v1/onboarding/status', () =>
      HttpResponse.json({ complete: true })
    )
  );

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/setup']}>
        <Routes>
          <Route element={<TestSetupGuard />}>
            <Route path="/setup" element={<div>Setup wizard</div>} />
          </Route>
          <Route path="/" element={<div>Home dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );

  // After queries resolve the guard redirects to "/" — wait for the home content
  await waitFor(() =>
    expect(screen.getByText('Home dashboard')).toBeInTheDocument()
  );
  expect(screen.queryByText('Setup wizard')).not.toBeInTheDocument();
});

test('SetupGuard shows setup page when onboarding is not complete', async () => {
  server.use(
    http.get('/api/v1/onboarding/status', () =>
      HttpResponse.json({ complete: false })
    )
  );

  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });

  render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/setup']}>
        <Routes>
          <Route element={<TestSetupGuard />}>
            <Route path="/setup" element={<div>Setup wizard</div>} />
          </Route>
          <Route path="/" element={<div>Home dashboard</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );

  await waitFor(() =>
    expect(screen.getByText('Setup wizard')).toBeInTheDocument()
  );
  expect(screen.queryByText('Home dashboard')).not.toBeInTheDocument();
});
