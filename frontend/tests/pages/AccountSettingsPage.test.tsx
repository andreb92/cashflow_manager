import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import AccountSettings from '../../src/pages/settings/AccountSettings';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/settings/account']}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

test('shows Change password button for password users', async () => {
  render(<AccountSettings />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /change password/i })).toBeInTheDocument());
});

test('hides Change password button for OIDC-only users', async () => {
  server.use(
    http.get('/api/v1/auth/me', () =>
      HttpResponse.json({ id: 'user-1', email: 'test@example.com', name: 'Test User', has_password: false, has_oidc: true })
    )
  );
  render(<AccountSettings />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument());
  expect(screen.queryByRole('button', { name: /change password/i })).not.toBeInTheDocument();
});

test('opens change password modal on button click', async () => {
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));
  expect(screen.getByLabelText(/current password/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/^new password/i)).toBeInTheDocument();
  expect(screen.getByLabelText(/confirm new password/i)).toBeInTheDocument();
});

test('submit button disabled when passwords do not match', async () => {
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));

  await user.type(screen.getByLabelText(/current password/i), 'oldpassword');
  await user.type(screen.getByLabelText(/^new password/i), 'newpassword1');
  await user.type(screen.getByLabelText(/confirm new password/i), 'different');

  expect(screen.getByRole('button', { name: /update password/i })).toBeDisabled();
});

test('shows mismatch error when passwords do not match', async () => {
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));

  await user.type(screen.getByLabelText(/^new password/i), 'newpassword1');
  await user.type(screen.getByLabelText(/confirm new password/i), 'different');

  expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument();
});

test('submit button disabled when new password is too short', async () => {
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));

  await user.type(screen.getByLabelText(/current password/i), 'oldpassword');
  await user.type(screen.getByLabelText(/^new password/i), 'short');
  await user.type(screen.getByLabelText(/confirm new password/i), 'short');

  expect(screen.getByRole('button', { name: /update password/i })).toBeDisabled();
});

test('shows success message after successful password change', async () => {
  server.use(
    http.put('/api/v1/users/me/password', () => HttpResponse.json({ ok: true }))
  );
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));

  await user.type(screen.getByLabelText(/current password/i), 'oldpassword');
  await user.type(screen.getByLabelText(/^new password/i), 'newpassword1');
  await user.type(screen.getByLabelText(/confirm new password/i), 'newpassword1');
  await user.click(screen.getByRole('button', { name: /update password/i }));

  await waitFor(() => expect(screen.getByText(/password changed successfully/i)).toBeInTheDocument());
});

test('shows API error message on failure', async () => {
  server.use(
    http.put('/api/v1/users/me/password', () =>
      HttpResponse.json({ detail: 'Current password is incorrect' }, { status: 401 })
    )
  );
  const user = userEvent.setup();
  render(<AccountSettings />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /change password/i }));
  await user.click(screen.getByRole('button', { name: /change password/i }));

  await user.type(screen.getByLabelText(/current password/i), 'wrongpassword');
  await user.type(screen.getByLabelText(/^new password/i), 'newpassword1');
  await user.type(screen.getByLabelText(/confirm new password/i), 'newpassword1');
  await user.click(screen.getByRole('button', { name: /update password/i }));

  await waitFor(() => expect(screen.getByText(/current password is incorrect/i)).toBeInTheDocument());
});
