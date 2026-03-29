import { apiClient } from './client';
import type { User } from '../types/api';

export const authApi = {
  me: () =>
    apiClient.get<User>('/auth/me').then((r) => r.data),
  login: (email: string, password: string) =>
    apiClient.post<User>('/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, name: string, password: string) =>
    apiClient.post<User>('/auth/register', { email, name, password }).then((r) => r.data),
  logout: () =>
    apiClient.post('/auth/logout'),
  oidcLoginUrl: () => '/api/v1/auth/oidc/login',
  deleteMe: () => apiClient.delete('/users/me'),
};

export async function fetchMeOrNull(): Promise<User | null> {
  try {
    return await authApi.me();
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr.response?.status === 401) return null;
    }
    throw err;
  }
}
