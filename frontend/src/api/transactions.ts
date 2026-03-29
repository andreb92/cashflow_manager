import { apiClient } from './client';
import type { Transaction } from '../types/api';

interface ListParams {
  billing_month?: string;  // dashboard/summary: filter by billing month
  date_month?: string;     // transactions page: filter by actual transaction date
  payment_method_id?: string;
  category_id?: string;
  parent_id?: string;
}

interface CreateBody {
  date: string;
  detail: string;
  amount: number;
  payment_method_id: string;
  category_id: string;
  transaction_direction: Transaction['transaction_direction'];
  recurrence_months?: number;
  installment_total?: number;
  notes?: string;
}

export const transactionsApi = {
  list: (params?: ListParams) =>
    apiClient.get<Transaction[]>('/transactions', { params }).then((r) => r.data),
  get: (id: string) =>
    apiClient.get<Transaction>(`/transactions/${id}`).then((r) => r.data),
  create: (body: CreateBody) =>
    apiClient.post<Transaction>('/transactions', body).then((r) => r.data),
  update: (id: string, body: Partial<CreateBody>, cascade?: string) =>
    apiClient.put<Transaction>(`/transactions/${id}`, body, { params: cascade ? { cascade } : {} }).then((r) => r.data),
  delete: (id: string, cascade?: string) =>
    apiClient.delete(`/transactions/${id}`, { params: cascade ? { cascade } : {} }),
};
