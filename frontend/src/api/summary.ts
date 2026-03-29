import { apiClient } from './client';
import type { MonthlySummary } from '../types/api';

export const summaryApi = {
  year: (year: number) =>
    apiClient.get<MonthlySummary[]>(`/summary/${year}`).then((r) => r.data),
  month: (year: number, month: number) =>
    apiClient.get<MonthlySummary>(`/summary/${year}/${month}`).then((r) => r.data),
};
