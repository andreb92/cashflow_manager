import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import App from '../../src/App';

function renderApp(path = '/') {
  window.history.pushState({}, '', path);
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>
  );
}

test('unauthenticated user is redirected to /login', async () => {
  server.use(
    http.get('/api/v1/auth/me', () => HttpResponse.json(null, { status: 401 }))
  );
  renderApp('/');
  await waitFor(() =>
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  );
});

test('authenticated user with onboarding complete sees dashboard', async () => {
  renderApp('/');
  await waitFor(() =>
    expect(screen.getByText(/dashboard/i)).toBeInTheDocument()
  );
});

test('authenticated user with incomplete onboarding is redirected to /setup', async () => {
  server.use(
    http.get('/api/v1/onboarding/status', () =>
      HttpResponse.json({ complete: false })
    )
  );
  renderApp('/');
  await waitFor(() =>
    expect(screen.getByText(/setup your account/i)).toBeInTheDocument()
  );
});
