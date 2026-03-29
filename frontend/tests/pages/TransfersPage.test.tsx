import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import TransfersPage from '../../src/pages/TransfersPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}><MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter></QueryClientProvider>
  );
}

beforeEach(() => {
  server.use(
    http.get('/api/v1/transfers', () =>
      HttpResponse.json([{
        id: 'tr1', user_id: 'u1', date: '2026-03-10', detail: 'Monthly saving',
        amount: 500, from_account_type: 'bank', from_account_name: 'MyBank',
        to_account_type: 'saving', to_account_name: 'SavingPot',
        billing_month: '2026-03-01', recurrence_months: 12, notes: null,
        parent_transfer_id: null, created_at: '',
      }])
    )
  );
});

test('TransfersPage lists transfers with from/to accounts', async () => {
  render(<TransfersPage />, { wrapper });
  await waitFor(() => expect(screen.getByText('Monthly saving')).toBeInTheDocument());
  expect(screen.getByText(/MyBank/)).toBeInTheDocument();
  expect(screen.getByText(/SavingPot/)).toBeInTheDocument();
});

test('TransfersPage opens add form', async () => {
  const user = userEvent.setup();
  render(<TransfersPage />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /add transfer/i }));
  await user.click(screen.getByRole('button', { name: /add transfer/i }));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
});
