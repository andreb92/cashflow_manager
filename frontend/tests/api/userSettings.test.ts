import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { userSettingsApi } from '../../src/api/userSettings';

describe('userSettingsApi', () => {
  it('upsert puts items and returns updated settings', async () => {
    const items = [{ key: 'theme', value: 'dark' }];
    server.use(
      http.put('/api/v1/user-settings', () => HttpResponse.json(items))
    );
    const result = await userSettingsApi.upsert(items);
    expect(result).toEqual(items);
  });

  it('upsert puts multiple items', async () => {
    const items = [
      { key: 'theme', value: 'dark' },
      { key: 'currency', value: 'USD' },
    ];
    server.use(
      http.put('/api/v1/user-settings', () => HttpResponse.json(items))
    );
    const result = await userSettingsApi.upsert(items);
    expect(result).toHaveLength(2);
  });
});
