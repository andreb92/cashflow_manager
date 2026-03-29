import { apiClient } from './client';
import type { AnalyticsCategoryRow, AnalyticsTransferRow } from '../types/api';

interface Params {
  from: string;
  to: string;
  category_ids?: string;
  payment_method_ids?: string;
  direction?: 'debit' | 'income' | 'credit' | 'all';
}

export const analyticsApi = {
  categories: (params: Params) =>
    apiClient.get<AnalyticsCategoryRow[]>('/analytics/categories', { params }).then((r) => r.data),
  transfers: (params: { from: string; to: string }) =>
    apiClient.get<AnalyticsTransferRow[]>('/analytics/transfers', { params }).then((r) => r.data),
};
