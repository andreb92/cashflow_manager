import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend,
  CartesianGrid, ResponsiveContainer,
} from 'recharts';
import type { AnalyticsCategoryRow, Category } from '../../types/api';

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#84cc16','#f97316'];

interface Props {
  data: AnalyticsCategoryRow[];
  categories: Category[];
}

export default function CumulativeLineChart({ data, categories }: Props) {
  const { chartData, catLabels } = useMemo(() => {
    const categoryMap = Object.fromEntries(categories.map((c) => [c.id, `${c.type}/${c.sub_type}`]));
    const months = Array.from(new Set(data.map((r) => r.month))).sort();
    const labels = Array.from(new Set(data.map((r) => categoryMap[r.category_id] ?? r.category_id)));
    const rowsByMonth = new Map<string, AnalyticsCategoryRow[]>();

    for (const row of data) {
      const bucket = rowsByMonth.get(row.month);
      if (bucket) {
        bucket.push(row);
      } else {
        rowsByMonth.set(row.month, [row]);
      }
    }

    const running: Record<string, number> = {};
    const rows = months.map((month) => {
      const row: Record<string, string | number> = { month };
      for (const entry of rowsByMonth.get(month) ?? []) {
        const label = categoryMap[entry.category_id] ?? entry.category_id;
        running[label] = (running[label] ?? 0) + entry.total_amount;
      }
      for (const label of labels) {
        row[label] = running[label] ?? 0;
      }
      return row;
    });

    return { chartData: rows, catLabels: labels };
  }, [categories, data]);

  return (
    <ResponsiveContainer width="100%" height={340}>
      <LineChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `€${v}`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => `€${Number(v).toLocaleString('it-IT', { minimumFractionDigits: 2 })}`} />
        <Legend />
        {catLabels.map((label, i) => (
          <Line key={label} type="monotone" dataKey={label} stroke={COLORS[i % COLORS.length]} dot={false} />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
