import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { categoriesApi } from '../../src/api/categories';

describe('categoriesApi', () => {
  it('list with default activeOnly=true returns categories', async () => {
    server.use(
      http.get('/api/v1/categories', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('active_only') === 'true') {
          return HttpResponse.json([{ id: 'cat-1', type: 'expense', sub_type: 'food' }]);
        }
        return HttpResponse.json([]);
      })
    );
    const result = await categoriesApi.list();
    expect(result).toEqual([{ id: 'cat-1', type: 'expense', sub_type: 'food' }]);
  });

  it('list with activeOnly=false returns all categories', async () => {
    server.use(
      http.get('/api/v1/categories', ({ request }) => {
        const url = new URL(request.url);
        if (url.searchParams.get('active_only') === 'false') {
          return HttpResponse.json([
            { id: 'cat-1', type: 'expense', sub_type: 'food' },
            { id: 'cat-2', type: 'income', sub_type: 'salary' },
          ]);
        }
        return HttpResponse.json([]);
      })
    );
    const result = await categoriesApi.list(false);
    expect(result).toHaveLength(2);
  });

  it('create posts and returns new category', async () => {
    const body = { type: 'expense', sub_type: 'transport' };
    server.use(
      http.post('/api/v1/categories', () => HttpResponse.json({ id: 'cat-3', ...body }))
    );
    const result = await categoriesApi.create(body);
    expect(result).toMatchObject({ id: 'cat-3', type: 'expense' });
  });

  it('update puts and returns updated category', async () => {
    server.use(
      http.put('/api/v1/categories/cat-1', () =>
        HttpResponse.json({ id: 'cat-1', type: 'expense', sub_type: 'groceries' })
      )
    );
    const result = await categoriesApi.update('cat-1', { sub_type: 'groceries' });
    expect(result).toMatchObject({ id: 'cat-1', sub_type: 'groceries' });
  });

  it('delete calls DELETE endpoint', async () => {
    server.use(
      http.delete('/api/v1/categories/cat-1', () => HttpResponse.json({ ok: true }))
    );
    await expect(categoriesApi.delete('cat-1')).resolves.toBeDefined();
  });
});
