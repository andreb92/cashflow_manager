import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { vi } from 'vitest';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import AccountSettings from '../../src/pages/settings/AccountSettings';
import { authApi } from '../../src/api/auth';

const deleteResponse = {} as Awaited<ReturnType<typeof authApi.deleteMe>>;

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

test('sign out uses the OIDC logout path', async () => {
  server.use(
    http.get('/api/v1/auth/me', () =>
      HttpResponse.json({ id: 'user-1', email: 'test@example.com', name: 'Test User', has_password: false, has_oidc: true })
    )
  );
  const oidcLogoutSpy = vi.spyOn(authApi, 'oidcLogoutUrl');
  const user = userEvent.setup();

  render(<AccountSettings />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /sign out/i })).toBeInTheDocument());

  await user.click(screen.getByRole('button', { name: /sign out/i }));

  expect(oidcLogoutSpy).toHaveBeenCalled();
  oidcLogoutSpy.mockRestore();
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

test('OIDC-only users can delete their account without entering a password', async () => {
  server.use(
    http.get('/api/v1/auth/me', () =>
      HttpResponse.json({ id: 'user-1', email: 'test@example.com', name: 'Test User', has_password: false, has_oidc: true })
    )
  );
  const deleteMeSpy = vi.spyOn(authApi, 'deleteMe').mockResolvedValue(deleteResponse);
  const user = userEvent.setup();

  render(<AccountSettings />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /delete account/i })).toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: /delete account/i }));

  expect(screen.queryByLabelText(/enter your password to confirm/i)).not.toBeInTheDocument();
  const deleteButton = screen.getByRole('button', { name: /permanently delete account/i });
  expect(deleteButton).toBeEnabled();

  await user.click(deleteButton);

  await waitFor(() => expect(deleteMeSpy).toHaveBeenCalledWith(undefined));
  deleteMeSpy.mockRestore();
});

test('password users must enter a password before deleting their account', async () => {
  const deleteMeSpy = vi.spyOn(authApi, 'deleteMe').mockResolvedValue(deleteResponse);
  const user = userEvent.setup();

  render(<AccountSettings />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /delete account/i })).toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: /delete account/i }));

  const deleteButton = screen.getByRole('button', { name: /permanently delete account/i });
  expect(screen.getByLabelText(/enter your password to confirm/i)).toBeInTheDocument();
  expect(deleteButton).toBeDisabled();

  await user.type(screen.getByLabelText(/enter your password to confirm/i), 'Password1!');
  expect(deleteButton).toBeEnabled();

  await user.click(deleteButton);

  await waitFor(() => expect(deleteMeSpy).toHaveBeenCalledWith('Password1!'));
  deleteMeSpy.mockRestore();
});
