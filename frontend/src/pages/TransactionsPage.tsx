import { useState } from 'react';
import TransactionList from '../components/transactions/TransactionList';

function buildMonthOptions() {
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  return months.map((label, i) => ({ value: String(i + 1).padStart(2, '0'), label }));
}

function buildYearOptions() {
  const currentYear = new Date().getFullYear();
  const years = [];
  for (let y = currentYear - 3; y <= currentYear + 1; y++) {
    years.push({ value: String(y), label: String(y) });
  }
  return years;
}

const MONTH_OPTIONS = buildMonthOptions();
const YEAR_OPTIONS = buildYearOptions();

export default function TransactionsPage() {
  const now = new Date();
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1).padStart(2, '0'));

  const dateMonth = `${year}-${month}`;

  return (
    <div className="max-w-3xl space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="text-xl font-bold text-primary flex-1">Transactions</h1>
        <select
          value={year}
          onChange={(e) => setYear(e.target.value)}
          className="border border-line rounded px-2 py-1 text-sm bg-surface text-primary"
        >
          {YEAR_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
        <select
          value={month}
          onChange={(e) => setMonth(e.target.value)}
          className="border border-line rounded px-2 py-1 text-sm bg-surface text-primary"
        >
          {MONTH_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>
      <TransactionList dateMonth={dateMonth} />
    </div>
  );
}
