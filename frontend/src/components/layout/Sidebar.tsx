import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { Button } from '../ui/Button';

const links = [
  { to: '/summary', label: 'Summary' },
  { to: '/', label: 'Dashboard' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/transfers', label: 'Transfers' },
  { to: '/assets', label: 'Assets' },
  { to: '/salary', label: 'Salary' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/forecasting', label: 'Forecasting' },
  { to: '/settings', label: 'Settings' },
];

export default function Sidebar() {
  const { logout } = useAuth();
  const { dark, toggle } = useTheme();
  return (
    <nav className="w-56 bg-surface border-r border-line flex flex-col py-4 gap-1">
      <div className="px-4 pb-4 font-bold text-lg text-blue-700 dark:text-blue-400">CashFlow</div>
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          className={({ isActive }) =>
            `px-4 py-2 text-sm rounded mx-2 ${isActive ? 'bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-medium' : 'text-secondary hover:bg-muted-bg'}`
          }
        >
          {l.label}
        </NavLink>
      ))}
      <div className="mt-auto px-4 flex flex-col gap-2">
        <button
          onClick={toggle}
          aria-label="Toggle dark mode"
          className="w-full text-left px-3 py-2 text-sm rounded text-secondary hover:bg-muted-bg transition-colors"
        >
          {dark ? '☀ Light mode' : '🌙 Dark mode'}
        </button>
        <Button variant="ghost" className="w-full text-left" onClick={logout}>
          Sign out
        </Button>
      </div>
    </nav>
  );
}
