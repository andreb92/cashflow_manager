import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { taxConfigApi } from '../../src/api/taxConfig';

describe('taxConfigApi', () => {
  it('list returns array of tax configs', async () => {
    server.use(
      http.get('/api/v1/tax-config', () =>
        HttpResponse.json([{ id: 'tc-1', name: 'Income Tax', rate: 0.2 }])
      )
    );
    const result = await taxConfigApi.list();
    expect(result).toEqual([{ id: 'tc-1', name: 'Income Tax', rate: 0.2 }]);
  });

  it('create posts and returns new tax config', async () => {
    const body = { name: 'GST', rate: 0.1, applies_to: 'all' };
    server.use(
      http.post('/api/v1/tax-config', () => HttpResponse.json({ id: 'tc-2', ...body }))
    );
    const result = await taxConfigApi.create(body as any);
    expect(result).toMatchObject({ id: 'tc-2', name: 'GST' });
  });

  it('update puts and returns updated tax config', async () => {
    server.use(
      http.put('/api/v1/tax-config/tc-1', () =>
        HttpResponse.json({ id: 'tc-1', name: 'Income Tax', rate: 0.25 })
      )
    );
    const result = await taxConfigApi.update('tc-1', { inps_rate: 0.25 });
    expect(result).toMatchObject({ id: 'tc-1', rate: 0.25 });
  });

  it('delete calls DELETE endpoint', async () => {
    server.use(
      http.delete('/api/v1/tax-config/tc-1', () => HttpResponse.json({ ok: true }))
    );
    await expect(taxConfigApi.delete('tc-1')).resolves.toBeDefined();
  });
});
