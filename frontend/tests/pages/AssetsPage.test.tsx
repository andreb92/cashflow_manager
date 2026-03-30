import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { AuthProvider } from '../../src/contexts/AuthContext';
import AssetsPage from '../../src/pages/AssetsPage';

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}><MemoryRouter><AuthProvider>{children}</AuthProvider></MemoryRouter></QueryClientProvider>
  );
}

const year = new Date().getFullYear();

beforeEach(() => {
  server.use(
    http.get(`/api/v1/assets/${year}`, () =>
      HttpResponse.json([
        { asset_type: 'saving', asset_name: 'EmergencyFund', computed_amount: 8000, manual_override: null, final_amount: 8000 },
        { asset_type: 'pension', asset_name: 'AXA', computed_amount: 3200, manual_override: 3500, final_amount: 3500 },
      ])
    )
  );
});

test('AssetsPage lists assets with computed and override amounts', async () => {
  render(<AssetsPage />, { wrapper });
  await waitFor(() => expect(screen.getByText('EmergencyFund')).toBeInTheDocument());
  expect(screen.getByText('AXA')).toBeInTheDocument();
  expect(screen.getAllByText(/manual/i).length).toBeGreaterThan(0);
});

test('AssetsPage shows year selector', async () => {
  render(<AssetsPage />, { wrapper });
  await waitFor(() => expect(screen.getByRole('spinbutton')).toBeInTheDocument());
});
