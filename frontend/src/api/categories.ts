import { apiClient } from './client';
import type { Category } from '../types/api';

export const categoriesApi = {
  list: (activeOnly = true) =>
    apiClient.get<Category[]>('/categories', { params: { active_only: activeOnly } }).then((r) => r.data),
  create: (body: { type: string; sub_type: string }) =>
    apiClient.post<Category>('/categories', body).then((r) => r.data),
  update: (id: string, body: Partial<Category>) =>
    apiClient.put<Category>(`/categories/${id}`, body).then((r) => r.data),
  delete: (id: string) =>
    apiClient.delete(`/categories/${id}`),
};
