import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../hooks/useAuth';
import { authApi } from '../../api/auth';
import { Button } from '../../components/ui/Button';
import Modal from '../../components/ui/Modal';
import { Input } from '../../components/ui/Input';

export default function AccountSettings() {
  const { user, logout } = useAuth();
  const qc = useQueryClient();
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [password, setPassword] = useState('');

  const { mutate: deleteAccount, isPending, error: deleteError } = useMutation({
    mutationFn: () => authApi.deleteMe(password),
    onSuccess: () => {
      // Don't call logout() — the backend already cleared the JWT cookie.
      // Calling authApi.logout() would hit a dead session.
      qc.clear();
      window.location.href = '/login';
    },
  });

  return (
    <div className="space-y-4 max-w-sm">
      <div className="bg-surface border border-line rounded-lg p-4 text-sm space-y-2">
        <div><span className="text-muted">Email: </span><span className="font-medium text-primary">{user?.email}</span></div>
        <div><span className="text-muted">Name: </span><span className="font-medium text-primary">{user?.name}</span></div>
        <div className="flex gap-2 text-xs text-faint">
          {user?.has_password && <span>Password auth</span>}
          {user?.has_oidc && <span>OIDC / SSO</span>}
        </div>
      </div>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={logout}>Sign out</Button>
        <Button
          variant="ghost"
          className="text-red-600 dark:text-red-400 hover:text-red-700"
          onClick={() => setDeleteOpen(true)}
        >
          Delete account
        </Button>
      </div>

      <Modal
        open={deleteOpen}
        onClose={() => { setDeleteOpen(false); setPassword(''); }}
        title="Delete account"
      >
        <div className="flex flex-col gap-4">
          <div className="text-sm text-secondary bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 space-y-1">
            <p className="font-semibold text-red-700 dark:text-red-400">This action is irreversible.</p>
            <p>All your data will be permanently deleted: transactions, transfers, salary configs, assets, forecasts, and your account.</p>
          </div>
          <Input
            label="Enter your password to confirm"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Password"
          />
          {deleteError && (
            <p className="text-xs text-red-600">Failed to delete account. Please try again.</p>
          )}
          <Button
            isLoading={isPending}
            className="bg-red-600 hover:bg-red-700 text-white disabled:opacity-50"
            disabled={!password || isPending}
            onClick={() => deleteAccount()}
          >
            Permanently delete account
          </Button>
        </div>
      </Modal>
    </div>
  );
}
