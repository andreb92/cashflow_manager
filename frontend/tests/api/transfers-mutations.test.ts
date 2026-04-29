import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { transfersApi } from '../../src/api/transfers';

describe('transfersApi - mutations', () => {
  it('list forwards from_account/to_account filters', async () => {
    const items = [{ id: 'tr-1' }];
    server.use(
      http.get('/api/v1/transfers', ({ request }) => {
        const url = new URL(request.url);
        if (
          url.searchParams.get('from_account') === 'Checking'
          && url.searchParams.get('to_account') === 'Savings'
          && url.searchParams.get('billing_month') === '2026-01'
        ) {
          return HttpResponse.json(items);
        }
        return new HttpResponse(null, { status: 400 });
      })
    );

    const result = await transfersApi.list({
      billing_month: '2026-01',
      from_account: 'Checking',
      to_account: 'Savings',
    });
    expect(result).toEqual(items);
  });

  it('update puts and returns updated transfer without cascade', async () => {
    const updated = { id: 'tr-1', detail: 'Updated transfer', amount: 500 };
    server.use(
      http.put('/api/v1/transfers/tr-1', ({ request }) => {
        const url = new URL(request.url);
        if (!url.searchParams.has('cascade')) {
          return HttpResponse.json(updated);
        }
        return HttpResponse.json({});
      })
    );
    const result = await transfersApi.update('tr-1', { detail: 'Updated transfer' });
    expect(result).toEqual(updated);
  });

  it('update puts with cascade param when provided', async () => {
    const updated = { id: 'tr-1', detail: 'Transfer', amount: 600 };
    server.use(
      http.put('/api/v1/transfers/tr-1', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('cascade') === 'future') {
          return HttpResponse.json(updated);
        }
        return HttpResponse.json({});
      })
    );
    const result = await transfersApi.update('tr-1', { amount: 600 }, 'future');
    expect(result).toEqual(updated);
  });

  it('delete calls DELETE endpoint without cascade', async () => {
    server.use(
      http.delete('/api/v1/transfers/tr-1', () => HttpResponse.json({ ok: true }))
    );
    await expect(transfersApi.delete('tr-1')).resolves.toBeDefined();
  });

  it('delete calls DELETE endpoint with cascade param', async () => {
    server.use(
      http.delete('/api/v1/transfers/tr-1', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('cascade') === 'all') {
          return HttpResponse.json({ ok: true });
        }
        return new HttpResponse(null, { status: 400 });
      })
    );
    await expect(transfersApi.delete('tr-1', 'all')).resolves.toBeDefined();
  });
});
