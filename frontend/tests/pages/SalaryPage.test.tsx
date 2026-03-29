import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import SalaryPage from '../../src/pages/SalaryPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}><MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter></QueryClientProvider>
  );
}

beforeEach(() => {
  server.use(
    http.get('/api/v1/salary', () =>
      HttpResponse.json([{
        id: 'sc1', user_id: 'u1', valid_from: '2026-01-01', ral: 42000,
        employer_contrib_rate: 0.04, voluntary_contrib_rate: 0, regional_tax_rate: 0.0173,
        municipal_tax_rate: 0.001, meal_vouchers_annual: 1320, welfare_annual: 500,
        manual_net_override: null, computed_net_monthly: 2600,
      }])
    ),
    http.get('/api/v1/salary/calculate', () =>
      HttpResponse.json({
        gross_annual: 42000, social_security: 3860, pension_deductible: 1680, taxable_base: 36460,
        income_tax_gross: 8846, employment_deduction: 1450, income_tax_net: 7396,
        regional_surtax: 630, municipal_surtax: 36,
        net_annual: 29518, net_monthly: 2459.83,
        meal_vouchers_monthly: 110, welfare_monthly: 41.67,
      })
    )
  );
});

test('SalaryPage shows salary config period', async () => {
  render(<SalaryPage />, { wrapper });
  await waitFor(() => expect(screen.getByText('2026-01-01')).toBeInTheDocument());
});

test('SalaryPage shows computed net monthly', async () => {
  render(<SalaryPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/2\.600/)).toBeInTheDocument()); // Italian locale: 2.600
});

test('SalaryPage shows salary breakdown when period selected', async () => {
  render(<SalaryPage />, { wrapper });
  await waitFor(() => screen.getByText('2026-01-01'));
  // Breakdown should show INPS
  expect(await screen.findByText(/inps/i)).toBeInTheDocument();
});
