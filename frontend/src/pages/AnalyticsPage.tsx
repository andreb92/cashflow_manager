import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../api/analytics';
import { categoriesApi } from '../api/categories';
import { paymentMethodsApi } from '../api/paymentMethods';
import AnalyticsFilters from '../components/analytics/AnalyticsFilters';
import CategoryBarChart from '../components/analytics/CategoryBarChart';
import CumulativeLineChart from '../components/analytics/CumulativeLineChart';
import { Button } from '../components/ui/Button';
import type { AnalyticsCategoryRow } from '../types/api';

type View = 'bar' | 'cumulative';
type FilterDirection = 'debit' | 'income' | 'credit' | 'all';
interface Filters {
  from: string;
  to: string;
  direction: FilterDirection;
  categoryIds: string[];
  paymentMethodIds: string[];
}

const year = new Date().getFullYear();
const defaultFrom = `${year}-01`;
const defaultTo = `${year}-12`;

export default function AnalyticsPage() {
  const [view, setView] = useState<View>('bar');
  const [filters, setFilters] = useState<Filters>({
    from: defaultFrom,
    to: defaultTo,
    direction: 'all',
    categoryIds: [],
    paymentMethodIds: [],
  });

  const { data: categoryRows = [] } = useQuery({
    queryKey: ['analytics', filters],
    queryFn: () =>
      analyticsApi.categories({
        from: filters.from,
        to: filters.to,
        direction: filters.direction,
        ...(filters.categoryIds.length ? { category_ids: filters.categoryIds.join(',') } : {}),
        ...(filters.paymentMethodIds.length ? { payment_method_ids: filters.paymentMethodIds.join(',') } : {}),
      }),
  });

  const { data: transferRows = [] } = useQuery({
    queryKey: ['analytics', 'transfers', filters.from, filters.to],
    queryFn: () => analyticsApi.transfers({ from: filters.from, to: filters.to }),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => categoriesApi.list(false),
  });
  const { data: paymentMethods = [] } = useQuery({
    queryKey: ['payment-methods'],
    queryFn: () => paymentMethodsApi.list(false),
  });

  // Convert transfer rows into AnalyticsCategoryRow entries so the existing
  // chart components can render them without modification. The category_id is
  // set to the desired display label (e.g. "→ My Savings") so that the chart's
  // fallback path (categoryMap[id] ?? id) shows a readable series name.
  const transferAsRows = useMemo<AnalyticsCategoryRow[]>(
    () =>
      transferRows.map((t) => ({
        category_id: `→ ${t.to_account_name}`,
        type: t.to_account_type,
        sub_type: 'transfer',
        month: t.month,
        total_amount: t.total_amount,
      })),
    [transferRows],
  );

  const rows = useMemo(
    () => [...categoryRows, ...transferAsRows],
    [categoryRows, transferAsRows],
  );

  return (
    <div className="max-w-5xl space-y-4">
      <h1 className="text-xl font-bold text-primary">Analytics</h1>
      <AnalyticsFilters
        filters={filters}
        categories={categories}
        paymentMethods={paymentMethods}
        onChange={setFilters}
      />
      <div className="flex gap-2">
        <Button variant={view === 'bar' ? 'primary' : 'secondary'} onClick={() => setView('bar')}>Bar chart</Button>
        <Button variant={view === 'cumulative' ? 'primary' : 'secondary'} onClick={() => setView('cumulative')}>Cumulative</Button>
      </div>
      <div className="bg-surface rounded-lg border border-line p-4">
        {rows.length === 0 ? (
          <p className="text-faint text-sm text-center py-12">No data for selected filters</p>
        ) : view === 'bar' ? (
          <CategoryBarChart data={rows} categories={categories} />
        ) : (
          <CumulativeLineChart data={rows} categories={categories} />
        )}
      </div>
    </div>
  );
}
