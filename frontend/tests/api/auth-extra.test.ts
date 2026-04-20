import { describe, it, expect } from 'vitest';
import { http, HttpResponse } from 'msw';
import { server } from '../mocks/server';
import { authApi } from '../../src/api/auth';

describe('authApi - additional coverage', () => {
  it('logout posts to /auth/logout', async () => {
    server.use(
      http.post('/api/v1/auth/logout', () => HttpResponse.json({ ok: true }))
    );
    await expect(authApi.logout()).resolves.toBeDefined();
  });

  it('oidcLoginUrl returns the OIDC login path string', () => {
    expect(authApi.oidcLoginUrl()).toBe('/api/v1/auth/oidc/login');
  });

  it('oidcLogoutUrl returns the OIDC logout path string', () => {
    expect(authApi.oidcLogoutUrl()).toBe('/api/v1/auth/oidc/logout');
  });

  it('deleteMe calls DELETE /users/me with password', async () => {
    let requestBody: unknown;
    server.use(
      http.delete('/api/v1/users/me', async ({ request }) => {
        requestBody = await request.json();
        return HttpResponse.json({ ok: true });
      })
    );
    await expect(authApi.deleteMe('Password1!')).resolves.toBeDefined();
    expect(requestBody).toEqual({ password: 'Password1!' });
  });

  it('deleteMe calls DELETE /users/me with an empty body when password is omitted', async () => {
    let requestBody: unknown;
    server.use(
      http.delete('/api/v1/users/me', async ({ request }) => {
        requestBody = await request.json();
        return HttpResponse.json({ ok: true });
      })
    );
    await expect(authApi.deleteMe()).resolves.toBeDefined();
    expect(requestBody).toEqual({});
  });

  it('register posts and returns user', async () => {
    const user = { id: 'u-1', email: 'new@example.com', name: 'New User' };
    server.use(
      http.post('/api/v1/auth/register', () => HttpResponse.json(user))
    );
    const result = await authApi.register('new@example.com', 'New User', 'password123');
    expect(result).toEqual(user);
  });
});
