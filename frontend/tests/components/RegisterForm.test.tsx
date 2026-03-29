import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import RegisterForm from '../../src/components/auth/RegisterForm';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

test('RegisterForm renders name, email, and password fields', () => {
  render(<RegisterForm />, { wrapper });
  expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/name/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
});

test('RegisterForm submitting with valid data calls the register API', async () => {
  let requestBody: unknown;
  server.use(
    http.post('/api/v1/auth/register', async ({ request }) => {
      requestBody = await request.json();
      return HttpResponse.json(
        { id: 'user-1', email: 'new@example.com', name: 'New User', has_password: true, has_oidc: false },
        { status: 200 }
      );
    })
  );
  const user = userEvent.setup();
  render(<RegisterForm />, { wrapper });
  await user.type(screen.getByLabelText(/email/i), 'new@example.com');
  await user.type(screen.getByLabelText(/name/i), 'New User');
  await user.type(screen.getByLabelText(/password/i), 'SecurePass1!');
  await user.click(screen.getByRole('button', { name: /create account/i }));
  await waitFor(() => {
    expect(requestBody).toMatchObject({
      email: 'new@example.com',
      name: 'New User',
      password: 'SecurePass1!',
    });
  });
});

test('RegisterForm shows error alert on failed registration', async () => {
  server.use(
    http.post('/api/v1/auth/register', () =>
      HttpResponse.json({ detail: 'Email already registered' }, { status: 400 })
    )
  );
  const user = userEvent.setup();
  render(<RegisterForm />, { wrapper });
  await user.type(screen.getByLabelText(/email/i), 'existing@example.com');
  await user.type(screen.getByLabelText(/name/i), 'Someone');
  await user.type(screen.getByLabelText(/password/i), 'SecurePass1!');
  await user.click(screen.getByRole('button', { name: /create account/i }));
  await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
});
