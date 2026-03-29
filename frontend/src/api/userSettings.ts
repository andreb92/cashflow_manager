import { apiClient } from './client';

export const userSettingsApi = {
  upsert: (items: { key: string; value: string }[]) =>
    apiClient.put('/user-settings', items).then((r) => r.data),
};
