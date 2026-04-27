import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import LoginForm from '../../src/components/auth/LoginForm';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('LoginForm renders email and password fields', () => {
  render(<LoginForm />, { wrapper });
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});

test('LoginForm shows error on failed login', async () => {
  server.use(
    http.post('/api/v1/auth/login', () =>
      HttpResponse.json({ detail: 'Invalid credentials' }, { status: 401 })
    )
  );
  const user = userEvent.setup();
  render(<LoginForm />, { wrapper });
  await user.type(screen.getByLabelText(/email/i), 'bad@test.com');
  await user.type(screen.getByLabelText(/password/i), 'wrong');
  await user.click(screen.getByRole('button', { name: /sign in/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
});

test('LoginForm shows OIDC link only when enabled', async () => {
  render(<LoginForm />, { wrapper });
  expect(await screen.findByRole('link', { name: /sign in with sso/i })).toBeInTheDocument();
});

test('LoginForm hides OIDC link when oidc is disabled', async () => {
  server.use(
    http.get('/api/v1/auth/config', () =>
      HttpResponse.json({
        oidc_enabled: false,
        basic_auth_enabled: true,
      })
    )
  );

  render(<LoginForm />, { wrapper });

  await waitFor(() => {
    expect(screen.queryByRole('link', { name: /sign in with sso/i })).not.toBeInTheDocument();
  });
});

test('LoginForm hides email/password sign-in when basic auth is disabled', async () => {
  server.use(
    http.get('/api/v1/auth/config', () =>
      HttpResponse.json({
        oidc_enabled: true,
        basic_auth_enabled: false,
      })
    )
  );

  render(<LoginForm />, { wrapper });

  expect(
    await screen.findByText(/email and password sign-in is disabled for this instance/i)
  ).toBeInTheDocument();
  expect(screen.queryByLabelText(/email/i)).not.toBeInTheDocument();
  expect(screen.queryByLabelText(/password/i)).not.toBeInTheDocument();
  expect(screen.queryByRole('button', { name: /sign in/i })).not.toBeInTheDocument();
  expect(screen.getByRole('link', { name: /sign in with sso/i })).toBeInTheDocument();
});
