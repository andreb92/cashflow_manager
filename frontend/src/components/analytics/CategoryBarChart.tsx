import {
  BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  CartesianGrid, ResponsiveContainer,
} from 'recharts';
import type { AnalyticsCategoryRow, Category } from '../../types/api';

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#84cc16','#f97316'];

interface Props {
  data: AnalyticsCategoryRow[];
  categories: Category[];
}

export default function CategoryBarChart({ data, categories }: Props) {
  const categoryMap = Object.fromEntries(categories.map((c) => [c.id, `${c.type}/${c.sub_type}`]));
  const months = Array.from(new Set(data.map((r) => r.month))).sort();
  const catLabels = Array.from(new Set(data.map((r) => categoryMap[r.category_id] ?? r.category_id)));

  const chartData = months.map((m) => {
    const row: Record<string, string | number> = { month: m };
    for (const d of data.filter((r) => r.month === m)) {
      const label = categoryMap[d.category_id] ?? d.category_id;
      row[label] = (Number(row[label]) || 0) + d.total_amount;
    }
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={340}>
      <BarChart data={chartData} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="month" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={(v) => `€${v}`} tick={{ fontSize: 11 }} />
        <Tooltip formatter={(v) => `€${Number(v).toLocaleString('it-IT', { minimumFractionDigits: 2 })}`} />
        <Legend />
        {catLabels.map((label, i) => (
          <Bar key={label} dataKey={label} stackId="a" fill={COLORS[i % COLORS.length]} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
