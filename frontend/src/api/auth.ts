import { apiClient } from './client';
import type { AuthConfig, User } from '../types/api';

const LEGACY_AUTH_CONFIG: AuthConfig = {
  oidc_enabled: true,
  basic_auth_enabled: true,
};

export const authApi = {
  me: () =>
    apiClient.get<User>('/auth/me').then((r) => r.data),
  config: () =>
    apiClient.get<AuthConfig>('/auth/config').then((r) => r.data),
  login: (email: string, password: string) =>
    apiClient.post<User>('/auth/login', { email, password }).then((r) => r.data),
  register: (email: string, name: string, password: string) =>
    apiClient.post<User>('/auth/register', { email, name, password }).then((r) => r.data),
  logout: () =>
    apiClient.post('/auth/logout'),
  oidcLogoutUrl: () => '/api/v1/auth/oidc/logout',
  oidcLoginUrl: () => '/api/v1/auth/oidc/login',
  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.put('/users/me/password', { current_password: currentPassword, new_password: newPassword }),
  deleteMe: (password?: string) =>
    apiClient.delete('/users/me', {
      data: password === undefined ? {} : { password },
    }),
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

export async function fetchAuthConfigOrLegacy(): Promise<AuthConfig> {
  try {
    return await authApi.config();
  } catch (err: unknown) {
    if (err && typeof err === 'object' && 'response' in err) {
      const axiosErr = err as { response?: { status?: number } };
      if (axiosErr.response?.status === 404) return LEGACY_AUTH_CONFIG;
    }
    throw err;
  }
}
