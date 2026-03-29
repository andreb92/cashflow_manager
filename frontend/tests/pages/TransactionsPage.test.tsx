import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import TransactionsPage from '../../src/pages/TransactionsPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

const mockTransactions = [
  {
    id: 'tx1', user_id: 'u1', date: '2026-03-15', detail: 'Grocery run',
    amount: 45.50, payment_method_id: 'pm1', category_id: 'cat1',
    transaction_direction: 'debit', billing_month: '2026-03-01',
    recurrence_months: null, installment_total: null, installment_index: null,
    parent_transaction_id: null, notes: null, created_at: '', updated_at: '',
  },
  {
    id: 'tx2', user_id: 'u1', date: '2026-03-01', detail: 'Salary',
    amount: 2800, payment_method_id: 'pm2', category_id: 'cat2',
    transaction_direction: 'income', billing_month: '2026-03-01',
    recurrence_months: 12, installment_total: null, installment_index: null,
    parent_transaction_id: null, notes: null, created_at: '', updated_at: '',
  },
];

beforeEach(() => {
  server.use(
    http.get('/api/v1/transactions', () => HttpResponse.json(mockTransactions)),
    http.get('/api/v1/payment-methods', () =>
      HttpResponse.json([{ id: 'pm1', name: 'Visa', type: 'credit_card', is_main_bank: false, is_active: true }])
    ),
    http.get('/api/v1/categories', () =>
      HttpResponse.json([{ id: 'cat1', type: 'Personal', sub_type: 'Food', is_active: true }])
    ),
  );
});

test('TransactionsPage lists transactions', async () => {
  render(<TransactionsPage />, { wrapper });
  await waitFor(() => expect(screen.getByText('Grocery run')).toBeInTheDocument());
  expect(screen.getByText('Salary')).toBeInTheDocument();
});

test('TransactionsPage shows recurring indicator for recurrence_months set', async () => {
  render(<TransactionsPage />, { wrapper });
  await waitFor(() => expect(screen.getByText('Salary')).toBeInTheDocument());
  expect(screen.getByTitle(/recurring/i)).toBeInTheDocument();
});

test('TransactionsPage opens add form when button clicked', async () => {
  const user = userEvent.setup();
  render(<TransactionsPage />, { wrapper });
  await waitFor(() => expect(screen.getByRole('button', { name: /add transaction/i })).toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: /add transaction/i }));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
});

test('TransactionForm shows billing hint for credit_card payment method', async () => {
  const user = userEvent.setup();
  render(<TransactionsPage />, { wrapper });
  await waitFor(() => screen.getByRole('button', { name: /add transaction/i }));
  await user.click(screen.getByRole('button', { name: /add transaction/i }));
  // Select credit_card method
  const methodSelect = screen.getByLabelText(/payment method/i);
  await user.selectOptions(methodSelect, 'pm1');
  expect(screen.getByText(/billed in/i)).toBeInTheDocument();
});
