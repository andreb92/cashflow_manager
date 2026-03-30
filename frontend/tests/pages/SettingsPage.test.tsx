import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import PaymentMethodsSettings from '../../src/pages/settings/PaymentMethodsSettings';
import CategoriesSettings from '../../src/pages/settings/CategoriesSettings';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={['/settings/payment-methods']}>
        <AuthProvider>{children}</AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  server.use(
    http.get('/api/v1/payment-methods', () =>
      HttpResponse.json([
        { id: 'pm1', name: 'Main Bank', type: 'bank', is_main_bank: true, linked_bank_id: null, opening_balance: 5000, is_active: true },
      ])
    ),
    http.get('/api/v1/categories', () =>
      HttpResponse.json([
        { id: 'cat1', type: 'Housing', sub_type: 'Home', is_active: true },
        { id: 'cat2', type: 'Personal', sub_type: 'Food', is_active: false },
      ])
    )
  );
});

test('PaymentMethodsSettings shows list of payment methods', async () => {
  render(<PaymentMethodsSettings />, { wrapper });
  await waitFor(() => expect(screen.getByText('Main Bank')).toBeInTheDocument());
});

test('CategoriesSettings shows active and inactive categories', async () => {
  render(<CategoriesSettings />, { wrapper });
  await waitFor(() => {
    expect(screen.getByText(/Housing/)).toBeInTheDocument();
    expect(screen.getByText(/Personal/)).toBeInTheDocument();
  });
});
