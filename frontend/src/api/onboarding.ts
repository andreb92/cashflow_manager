import { apiClient } from './client';
import type { OnboardingPayload } from '../types/api';

export const onboardingApi = {
  status: () =>
    apiClient.get<{ complete: boolean }>('/onboarding/status').then((r) => r.data),
  submit: (body: OnboardingPayload) =>
    apiClient.post('/onboarding', body).then((r) => r.data),
};
