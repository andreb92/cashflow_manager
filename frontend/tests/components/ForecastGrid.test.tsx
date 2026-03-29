import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ForecastGrid from '../../src/components/forecasting/ForecastGrid';
import type { ForecastProjection } from '../../src/types/api';

const projection: ForecastProjection = {
  forecast_id: 'f1',
  base_year: 2025,
  projection_years: 1,
  period: { from: '2026-01', to: '2026-12' },
  lines: [
    {
      line_id: 'l1',
      detail: 'Rent',
      category_id: null,
      base_amount: 900,
      billing_day: 1,
      adjustments: [],
      months: [
        { month: '2026-01', effective_amount: 900 },
        { month: '2026-02', effective_amount: 900 },
      ],
    },
  ],
  monthly_totals: [
    { month: '2026-01', total: 900 },
    { month: '2026-02', total: 900 },
  ],
  yearly_totals: [{ year: 2026, total: 10800 }],
};

test('ForecastGrid renders line details and effective amounts', () => {
  const qc = new QueryClient();
  render(
    <QueryClientProvider client={qc}>
      <ForecastGrid projection={projection} onAddAdjustment={() => {}} />
    </QueryClientProvider>
  );
  expect(screen.getByText('Rent')).toBeInTheDocument();
  expect(screen.getAllByText('900,00').length).toBeGreaterThan(0);
});

test('ForecastGrid shows yearly total', () => {
  const qc = new QueryClient();
  render(
    <QueryClientProvider client={qc}>
      <ForecastGrid projection={projection} onAddAdjustment={() => {}} />
    </QueryClientProvider>
  );
  expect(screen.getAllByText(/10\.800/).length).toBeGreaterThan(0);
});
