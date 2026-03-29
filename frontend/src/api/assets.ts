import { apiClient } from './client';
import type { Asset } from '../types/api';

export const assetsApi = {
  year: (year: number) =>
    apiClient.get<Asset[]>(`/assets/${year}`).then((r) => r.data),
  setOverride: (year: number, assetType: string, assetName: string, amount: number | null) =>
    apiClient.put(`/assets/${year}/${assetType}/${encodeURIComponent(assetName)}`, { manual_override: amount }),
};
