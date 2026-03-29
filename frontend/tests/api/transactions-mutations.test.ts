import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { transactionsApi } from '../../src/api/transactions';

describe('transactionsApi - mutations', () => {
  it('update puts and returns updated transaction without cascade', async () => {
    const updated = { id: 'tx-1', detail: 'Updated detail', amount: 100 };
    server.use(
      http.put('/api/v1/transactions/tx-1', ({ request }) => {
        const url = new URL(request.url);
        if (!url.searchParams.has('cascade')) {
          return HttpResponse.json(updated);
        }
        return HttpResponse.json({});
      })
    );
    const result = await transactionsApi.update('tx-1', { detail: 'Updated detail' });
    expect(result).toEqual(updated);
  });

  it('update puts with cascade param when provided', async () => {
    const updated = { id: 'tx-1', detail: 'Updated', amount: 200 };
    server.use(
      http.put('/api/v1/transactions/tx-1', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('cascade') === 'future') {
          return HttpResponse.json(updated);
        }
        return HttpResponse.json({});
      })
    );
    const result = await transactionsApi.update('tx-1', { amount: 200 }, 'future');
    expect(result).toEqual(updated);
  });

  it('delete calls DELETE endpoint without cascade', async () => {
    server.use(
      http.delete('/api/v1/transactions/tx-1', () => HttpResponse.json({ ok: true }))
    );
    await expect(transactionsApi.delete('tx-1')).resolves.toBeDefined();
  });

  it('delete calls DELETE endpoint with cascade param', async () => {
    server.use(
      http.delete('/api/v1/transactions/tx-1', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('cascade') === 'all') {
          return HttpResponse.json({ ok: true });
        }
        return new HttpResponse(null, { status: 400 });
      })
    );
    await expect(transactionsApi.delete('tx-1', 'all')).resolves.toBeDefined();
  });
});
