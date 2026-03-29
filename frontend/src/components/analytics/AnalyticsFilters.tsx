import type { Category, PaymentMethod } from '../../types/api';

interface Filters {
  from: string;
  to: string;
  direction: 'debit' | 'income' | 'credit' | 'all';
  categoryIds: string[];
  paymentMethodIds: string[];
}

interface Props {
  filters: Filters;
  categories: Category[];
  paymentMethods: PaymentMethod[];
  onChange: (f: Filters) => void;
}

export default function AnalyticsFilters({ filters, categories, paymentMethods, onChange }: Props) {
  const toggleCat = (id: string) =>
    onChange({
      ...filters,
      categoryIds: filters.categoryIds.includes(id)
        ? filters.categoryIds.filter((c) => c !== id)
        : [...filters.categoryIds, id],
    });

  const togglePM = (id: string) =>
    onChange({
      ...filters,
      paymentMethodIds: filters.paymentMethodIds.includes(id)
        ? filters.paymentMethodIds.filter((p) => p !== id)
        : [...filters.paymentMethodIds, id],
    });

  return (
    <div className="bg-surface border border-line rounded-lg p-4 space-y-3 text-sm">
      <div className="flex gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted font-medium">From</label>
          <input type="month" value={filters.from} onChange={(e) => onChange({ ...filters, from: e.target.value })}
            className="border border-line-strong rounded px-2 py-1 bg-elevated text-primary" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted font-medium">To</label>
          <input type="month" value={filters.to} onChange={(e) => onChange({ ...filters, to: e.target.value })}
            className="border border-line-strong rounded px-2 py-1 bg-elevated text-primary" />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-muted font-medium">Direction</label>
          <select value={filters.direction} onChange={(e) => onChange({ ...filters, direction: e.target.value as Filters['direction'] })}
            className="border border-line-strong rounded px-2 py-1 bg-elevated text-primary">
            <option value="all">All</option>
            <option value="debit">Debit</option>
            <option value="income">Income</option>
            <option value="credit">Credit</option>
          </select>
        </div>
      </div>
      {categories.length > 0 && (
        <div>
          <p className="text-xs text-muted font-medium mb-1">Categories</p>
          <div className="flex flex-wrap gap-1">
            {categories.map((c) => (
              <button
                key={c.id}
                onClick={() => toggleCat(c.id)}
                className={`px-2 py-0.5 rounded-full text-xs border ${filters.categoryIds.includes(c.id) ? 'bg-blue-600 text-white border-blue-600' : 'border-line-strong text-secondary'}`}
              >
                {c.type}/{c.sub_type}
              </button>
            ))}
          </div>
        </div>
      )}
      {paymentMethods.length > 0 && (
        <div>
          <p className="text-xs text-muted font-medium mb-1">Payment methods</p>
          <div className="flex flex-wrap gap-1">
            {paymentMethods.map((m) => (
              <button
                key={m.id}
                onClick={() => togglePM(m.id)}
                className={`px-2 py-0.5 rounded-full text-xs border ${filters.paymentMethodIds.includes(m.id) ? 'bg-blue-600 text-white border-blue-600' : 'border-line-strong text-secondary'}`}
              >
                {m.name}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
