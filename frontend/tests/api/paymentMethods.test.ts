import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { paymentMethodsApi } from '../../src/api/paymentMethods';

describe('paymentMethodsApi', () => {
  it('list with default activeOnly=true returns active payment methods', async () => {
    server.use(
      http.get('/api/v1/payment-methods', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('active_only') === 'true') {
          return HttpResponse.json([{ id: 'pm-1', name: 'Checking', type: 'bank' }]);
        }
        return HttpResponse.json([]);
      })
    );
    const result = await paymentMethodsApi.list();
    expect(result).toEqual([{ id: 'pm-1', name: 'Checking', type: 'bank' }]);
  });

  it('list with activeOnly=false returns all payment methods', async () => {
    server.use(
      http.get('/api/v1/payment-methods', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('active_only') === 'false') {
          return HttpResponse.json([
            { id: 'pm-1', name: 'Checking', type: 'bank' },
            { id: 'pm-2', name: 'Old Card', type: 'credit_card' },
          ]);
        }
        return HttpResponse.json([]);
      })
    );
    const result = await paymentMethodsApi.list(false);
    expect(result).toHaveLength(2);
  });

  it('create posts and returns new payment method', async () => {
    const body = { name: 'Savings', type: 'bank', is_main_bank: false, is_active: true };
    server.use(
      http.post('/api/v1/payment-methods', () => HttpResponse.json({ id: 'pm-3', ...body }))
    );
    const result = await paymentMethodsApi.create(body as any);
    expect(result).toMatchObject({ id: 'pm-3', name: 'Savings' });
  });

  it('update puts and returns updated payment method', async () => {
    server.use(
      http.put('/api/v1/payment-methods/pm-1', () =>
        HttpResponse.json({ id: 'pm-1', name: 'Main Checking', type: 'bank' })
      )
    );
    const result = await paymentMethodsApi.update('pm-1', { name: 'Main Checking' });
    expect(result).toMatchObject({ id: 'pm-1', name: 'Main Checking' });
  });

  it('setMainBank posts to set-main-bank endpoint', async () => {
    server.use(
      http.post('/api/v1/payment-methods/pm-1/set-main-bank', () =>
        HttpResponse.json({ ok: true })
      )
    );
    await expect(paymentMethodsApi.setMainBank('pm-1', 1000)).resolves.toBeDefined();
  });

  it('history returns main bank history', async () => {
    const historyData = [{ date: '2026-01-01', balance: 5000 }];
    server.use(
      http.get('/api/v1/payment-methods/main-bank-history', () => HttpResponse.json(historyData))
    );
    const result = await paymentMethodsApi.history();
    expect(result).toEqual(historyData);
  });
});
