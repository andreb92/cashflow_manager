import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import { useAuth } from '../../src/hooks/useAuth';

function TestComponent() {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div>loading</div>;
  return <div>{user?.email ?? 'no-user'}</div>;
}

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}><AuthProvider>{children}</AuthProvider></QueryClientProvider>;
}

test('AuthContext provides user from /auth/me', async () => {
  render(<TestComponent />, { wrapper });
  await waitFor(() => expect(screen.getByText('test@example.com')).toBeInTheDocument());
});

test('AuthContext shows loading state initially', () => {
  render(<TestComponent />, { wrapper });
  expect(screen.getByText('loading')).toBeInTheDocument();
});

test('AuthContext returns null user on 401', async () => {
  server.use(
    http.get('/api/v1/auth/me', () => HttpResponse.json(null, { status: 401 }))
  );
  render(<TestComponent />, { wrapper });
  await waitFor(() => expect(screen.getByText('no-user')).toBeInTheDocument());
});
