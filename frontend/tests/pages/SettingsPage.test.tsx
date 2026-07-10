import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

test('CategoriesSettings marks inactive categories and offers a Reactivate action', async () => {
  render(<CategoriesSettings />, { wrapper });
  await waitFor(() => expect(screen.getByText(/Personal/)).toBeInTheDocument());

  const inactiveRow = screen.getByText(/Personal/).closest('li')!;
  expect(within(inactiveRow).getByText(/inactive/i)).toBeInTheDocument();
  expect(within(inactiveRow).getByRole('button', { name: /reactivate/i })).toBeInTheDocument();

  const activeRow = screen.getByText(/Housing/).closest('li')!;
  expect(within(activeRow).queryByText(/inactive/i)).not.toBeInTheDocument();
  expect(within(activeRow).getByRole('button', { name: /deactivate/i })).toBeInTheDocument();
});

test('CategoriesSettings reactivates a deactivated category', async () => {
  const user = userEvent.setup();
  let requestBody: unknown;

  server.use(
    http.put('/api/v1/categories/cat2', async ({ request }) => {
      requestBody = await request.json();
      return HttpResponse.json({ id: 'cat2', type: 'Personal', sub_type: 'Food', is_active: true });
    })
  );

  render(<CategoriesSettings />, { wrapper });
  await waitFor(() => expect(screen.getByText(/Personal/)).toBeInTheDocument());

  const inactiveRow = screen.getByText(/Personal/).closest('li')!;
  await user.click(within(inactiveRow).getByRole('button', { name: /reactivate/i }));

  await waitFor(() => expect(requestBody).toEqual({ is_active: true }));
});
