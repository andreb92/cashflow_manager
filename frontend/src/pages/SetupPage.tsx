import React from 'react';
import { OnboardingProvider, useOnboarding } from '../contexts/OnboardingContext';
import WizardProgress from '../components/onboarding/WizardProgress';
import StepStartDate from '../components/onboarding/StepStartDate';
import StepMainBank from '../components/onboarding/StepMainBank';
import StepAdditionalBanks from '../components/onboarding/StepAdditionalBanks';
import StepPaymentMethods from '../components/onboarding/StepPaymentMethods';
import StepSavingAccounts from '../components/onboarding/StepSavingAccounts';
import StepInvestmentAccounts from '../components/onboarding/StepInvestmentAccounts';
import StepSalaryConfig from '../components/onboarding/StepSalaryConfig';
import StepReview from '../components/onboarding/StepReview';

const STEPS: Record<number, React.ComponentType> = {
  1: StepStartDate,
  2: StepMainBank,
  3: StepAdditionalBanks,
  4: StepPaymentMethods,
  5: StepSavingAccounts,
  6: StepInvestmentAccounts,
  7: StepSalaryConfig,
  8: StepReview,
};

function WizardContent() {
  const { step } = useOnboarding();
  const Step = STEPS[step];
  return (
    <div className="min-h-screen bg-gray-50 flex items-start justify-center pt-16 px-4">
      <div className="bg-white rounded-lg shadow-sm border p-8 w-full max-w-lg">
        <h1 className="text-xl font-bold mb-4 text-primary">Setup your account</h1>
        <WizardProgress current={step} total={8} />
        <Step />
      </div>
    </div>
  );
}

export default function SetupPage() {
  return (
    <OnboardingProvider>
      <WizardContent />
    </OnboardingProvider>
  );
}
