import { apiClient } from './client';
import type { TaxConfig } from '../types/api';

export const taxConfigApi = {
  list: () =>
    apiClient.get<TaxConfig[]>('/tax-config').then((r) => r.data),
  create: (body: Omit<TaxConfig, 'id'>) =>
    apiClient.post<TaxConfig>('/tax-config', body).then((r) => r.data),
  update: (id: string, body: Partial<TaxConfig>) =>
    apiClient.put<TaxConfig>(`/tax-config/${id}`, body).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/tax-config/${id}`),
};
