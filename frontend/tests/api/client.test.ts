import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { apiClient } from '../../src/api/client';

describe('apiClient', () => {
  it('sends requests to /api/v1 base URL', async () => {
    server.use(
      http.get('/api/v1/ping', () => HttpResponse.json({ ok: true }))
    );
    const res = await apiClient.get('/ping');
    expect(res.data).toEqual({ ok: true });
  });

  it('includes credentials with requests', () => {
    expect(apiClient.defaults.withCredentials).toBe(true);
  });
});
