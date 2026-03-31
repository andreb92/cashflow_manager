import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import DashboardPage from '../../src/pages/DashboardPage';

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

beforeEach(() => {
  const year = new Date().getFullYear();
  const month = new Date().getMonth() + 1;
  server.use(
    http.get(`/api/v1/summary/${year}/${month}`, () =>
      HttpResponse.json({
        year, month,
        incomes: 3000,
        outcomes_by_method: { 'Visa': 800, 'Cash': 50 },
        transfers_out_bank: 200,
        transfers_in_bank: 0,
        bank_balance: 4500,
      })
    ),
    http.get(`/api/v1/assets/${year}`, () =>
      HttpResponse.json([
        { asset_type: 'saving', asset_name: 'SavingAccount', computed_amount: 10000, manual_override: null, final_amount: 10000 },
      ])
    )
  );
});

test('DashboardPage renders without crashing', async () => {
  render(<DashboardPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/bank balance/i)).toBeInTheDocument());
});

test('DashboardPage shows current month income and outcomes', async () => {
  render(<DashboardPage />, { wrapper });
  // Income label and formatted value from mocked data (3000 → "3.000,00")
  await waitFor(() => expect(screen.getByText(/income/i)).toBeInTheDocument());
  expect(screen.getByText(/3\.000/)).toBeInTheDocument();
  // Outcomes by method section shows the Visa entry (800 → "800,00")
  expect(screen.getByText('Visa')).toBeInTheDocument();
  expect(screen.getByText(/800/)).toBeInTheDocument();
});

test('DashboardPage shows bank balance for current month', async () => {
  render(<DashboardPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/4\.500/)).toBeInTheDocument());
});

test('DashboardPage shows total incomes', async () => {
  render(<DashboardPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/3\.000/)).toBeInTheDocument());
});

test('DashboardPage shows saving account in asset strip', async () => {
  render(<DashboardPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/SavingAccount/i)).toBeInTheDocument());
});
