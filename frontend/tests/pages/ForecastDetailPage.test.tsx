import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import ForecastDetailPage from '../../src/pages/ForecastDetailPage';

function makeWrapper(forecastId = 'fc1') {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return (
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={[`/forecasting/${forecastId}`]}>
          <AuthProvider>
            <Routes>
              <Route path="/forecasting/:id" element={children} />
            </Routes>
          </AuthProvider>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

const mockForecast = {
  id: 'fc1',
  name: 'Budget 2026',
  base_year: 2026,
  projection_years: 3,
  user_id: 'u1',
  created_at: '',
};

const mockProjection = {
  forecast_id: 'fc1',
  base_year: 2026,
  projection_years: 3,
  period: { from: '2026-01', to: '2028-12' },
  lines: [
    {
      line_id: 'line1',
      detail: 'Rent',
      category_id: null,
      base_amount: 800,
      billing_day: 1,
      adjustments: [],
      months: [
        { month: '2026-01', effective_amount: 800 },
        { month: '2026-02', effective_amount: 800 },
        { month: '2026-03', effective_amount: 800 },
      ],
    },
  ],
  monthly_totals: [
    { month: '2026-01', total: 800 },
    { month: '2026-02', total: 800 },
    { month: '2026-03', total: 800 },
  ],
  yearly_totals: [
    { year: 2026, total: 9600 },
    { year: 2027, total: 9600 },
    { year: 2028, total: 9600 },
  ],
};

beforeEach(() => {
  server.use(
    http.get('/api/v1/forecasts/fc1', () => HttpResponse.json(mockForecast)),
    http.get('/api/v1/forecasts/fc1/projection', () => HttpResponse.json(mockProjection)),
    http.get('/api/v1/payment-methods', () => HttpResponse.json([])),
    http.get('/api/v1/categories', () => HttpResponse.json([])),
  );
});

test('ForecastDetailPage renders without crashing and shows forecast name', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByText('Budget 2026')).toBeInTheDocument());
});

test('ForecastDetailPage shows base year and projection years', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByText('Budget 2026')).toBeInTheDocument());
  expect(screen.getByText(/base year: 2026/i)).toBeInTheDocument();
  expect(screen.getByText(/3-year projection/i)).toBeInTheDocument();
});

test('ForecastDetailPage shows forecast line detail in the grid', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByText('Rent')).toBeInTheDocument());
});

test('ForecastDetailPage shows base_amount formatted in the grid', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  // Rent is 800 per month, formatted as "800,00" in Italian locale
  await waitFor(() => expect(screen.getAllByText(/800,00/).length).toBeGreaterThan(0));
});

test('ForecastDetailPage has an add-adjustment button for each line', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByText('Rent')).toBeInTheDocument());
  // ForecastGrid renders a "+adj" button per line
  expect(screen.getByRole('button', { name: /\+adj/i })).toBeInTheDocument();
});

test('ForecastDetailPage clicking +adj opens AdjustmentModal', async () => {
  const user = userEvent.setup();
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByRole('button', { name: /\+adj/i })).toBeInTheDocument());
  await user.click(screen.getByRole('button', { name: /\+adj/i }));
  expect(screen.getByRole('dialog')).toBeInTheDocument();
  // AdjustmentModal title is an h2 with "Add adjustment"
  expect(screen.getByRole('heading', { name: /add adjustment/i })).toBeInTheDocument();
});

test('ForecastDetailPage shows yearly totals in the footer', async () => {
  render(<ForecastDetailPage />, { wrapper: makeWrapper() });
  await waitFor(() => expect(screen.getByText('Rent')).toBeInTheDocument());
  // yearly_totals rendered as "<strong>2026:</strong> €9.600,00" — check for "2026:" text node
  expect(screen.getByText(/2026:/)).toBeInTheDocument();
});
