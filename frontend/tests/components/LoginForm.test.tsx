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

test('LoginForm shows OIDC link', () => {
  render(<LoginForm />, { wrapper });
  expect(screen.getByRole('link', { name: /sign in with sso/i })).toBeInTheDocument();
});
