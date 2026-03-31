import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import SummaryPage from '../../src/pages/SummaryPage';

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

const year = new Date().getFullYear();

beforeEach(() => {
  const months = Array.from({ length: 12 }, (_, i) => ({
    year, month: i + 1,
    incomes: 3000, outcomes_by_method: { Visa: 500 },
    transfers_out_bank: 100, transfers_in_bank: 0, bank_balance: 5000 + i * 100,
  }));
  server.use(http.get(`/api/v1/summary/${year}`, () => HttpResponse.json(months)));
});

test('SummaryPage shows 12 month columns', async () => {
  render(<SummaryPage />, { wrapper });
  await waitFor(() => expect(screen.getAllByRole('columnheader')).toHaveLength(13)); // year + 12 months
});

test('SummaryPage shows year selector', async () => {
  render(<SummaryPage />, { wrapper });
  await waitFor(() => expect(screen.getByRole('spinbutton')).toBeInTheDocument());
});

test('SummaryPage renders without crashing', async () => {
  render(<SummaryPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/monthly summary/i)).toBeInTheDocument());
});

test('SummaryPage shows stamp_duty in monthly row', async () => {
  server.use(
    http.get(`/api/v1/summary/${year}`, () =>
      HttpResponse.json(
        Array.from({ length: 12 }, (_, i) => ({
          year, month: i + 1,
          incomes: 3000,
          outcomes_by_method: { Visa: 500 },
          transfers_out_bank: 100,
          transfers_in_bank: 0,
          bank_balance: 5000 + i * 100,
          stamp_duty: i === 0 ? 2 : 0,
        }))
      )
    )
  );
  render(<SummaryPage />, { wrapper });
  // The Stamp duty row label is rendered
  await waitFor(() => expect(screen.getByText('Stamp duty')).toBeInTheDocument());
  // The value "2,00" appears in the stamp duty row (Italian format: 2 → "2,00")
  expect(screen.getByText('2,00')).toBeInTheDocument();
});
