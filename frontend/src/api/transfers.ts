import { apiClient } from './client';
import type { Transfer } from '../types/api';

interface CreateBody {
  date: string;
  detail: string;
  amount: number;
  from_account_type: Transfer['from_account_type'];
  from_account_name: string;
  to_account_type: Transfer['to_account_type'];
  to_account_name: string;
  recurrence_months?: number;
  notes?: string;
}

export const transfersApi = {
  list: (params?: { billing_month?: string; account?: string; limit?: number; offset?: number }) =>
    apiClient.get<Transfer[]>('/transfers', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get<Transfer>(`/transfers/${id}`).then((r) => r.data),
  create: (body: CreateBody) =>
    apiClient.post<Transfer>('/transfers', body).then((r) => r.data),
  update: (id: string, body: Partial<CreateBody>, cascade?: string) =>
    apiClient.put<Transfer>(`/transfers/${id}`, body, { params: cascade ? { cascade } : undefined }).then((r) => r.data),
  delete: (id: string, cascade?: string) =>
    apiClient.delete(`/transfers/${id}`, { params: cascade ? { cascade } : undefined }),
};
