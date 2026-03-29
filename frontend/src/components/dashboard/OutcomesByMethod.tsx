import type { MonthlySummary } from '../../types/api';
import { fmt } from '../../utils/format';

interface Props { summary: MonthlySummary | undefined; isLoading: boolean; }

export default function OutcomesByMethod({ summary, isLoading }: Props) {
  if (isLoading) return <div className="bg-surface rounded-lg border border-line p-6 animate-pulse h-32" />;
  const methods = Object.entries(summary?.outcomes_by_method ?? {});
  return (
    <div className="bg-surface rounded-lg border border-line p-6">
      <p className="text-sm text-muted mb-3">Outcomes by payment method</p>
      {methods.length === 0 ? (
        <p className="text-faint text-sm">No outcomes this month</p>
      ) : (
        <ul className="space-y-2">
          {methods.map(([method, amount]) => (
            <li key={method} className="flex justify-between text-sm">
              <span className="text-primary">{method}</span>
              <span className="font-medium text-red-500">-€{fmt(amount)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
