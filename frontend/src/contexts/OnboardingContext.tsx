import React, { createContext, useContext, useState } from 'react';
import type { OnboardingPayload } from '../types/api';

interface OnboardingState {
  step: number;
  data: Partial<OnboardingPayload>;
  setStep: (n: number) => void;
  updateData: (patch: Partial<OnboardingPayload>) => void;
}

const OnboardingContext = createContext<OnboardingState | null>(null);

export function OnboardingProvider({ children }: { children: React.ReactNode }) {
  const [step, setStep] = useState(1);
  const [data, setData] = useState<Partial<OnboardingPayload>>({});

  const updateData = (patch: Partial<OnboardingPayload>) =>
    setData((prev) => ({ ...prev, ...patch }));

  return (
    <OnboardingContext.Provider value={{ step, data, setStep, updateData }}>
      {children}
    </OnboardingContext.Provider>
  );
}

export function useOnboarding() {
  const ctx = useContext(OnboardingContext);
  if (!ctx) throw new Error('useOnboarding must be used inside OnboardingProvider');
  return ctx;
}
