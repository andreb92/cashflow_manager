import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import AnalyticsPage from '../../src/pages/AnalyticsPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}><MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter></QueryClientProvider>
  );
}

const year = new Date().getFullYear();

beforeEach(() => {
  server.use(
    http.get('/api/v1/analytics/categories', () =>
      HttpResponse.json([
        { category_id: 'cat1', type: 'Personal', sub_type: 'Food', month: `${year}-01`, total_amount: 250 },
        { category_id: 'cat1', type: 'Personal', sub_type: 'Food', month: `${year}-02`, total_amount: 300 },
        { category_id: 'cat2', type: 'Leisure', sub_type: 'Restaurants', month: `${year}-01`, total_amount: 80 },
      ])
    ),
    http.get('/api/v1/categories', () =>
      HttpResponse.json([
        { id: 'cat1', type: 'Personal', sub_type: 'Food', is_active: true },
        { id: 'cat2', type: 'Leisure', sub_type: 'Restaurants', is_active: true },
      ])
    ),
    http.get('/api/v1/payment-methods', () => HttpResponse.json([]))
  );
});

test('AnalyticsPage renders without crashing', async () => {
  render(<AnalyticsPage />, { wrapper });
  await waitFor(() => expect(screen.getByText(/analytics/i)).toBeInTheDocument());
});

test('AnalyticsPage shows chart tabs for bar and line views', async () => {
  render(<AnalyticsPage />, { wrapper });
  await waitFor(() => {
    expect(screen.getByRole('button', { name: /bar/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /cumulative/i })).toBeInTheDocument();
  });
});
