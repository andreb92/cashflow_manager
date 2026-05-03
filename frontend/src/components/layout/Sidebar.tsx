import { NavLink } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';
import { Button } from '../ui/Button';

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/summary', label: 'Summary' },
  { to: '/transactions', label: 'Transactions' },
  { to: '/transfers', label: 'Transfers' },
  { to: '/assets', label: 'Assets' },
  { to: '/salary', label: 'Salary' },
  { to: '/analytics', label: 'Analytics' },
  { to: '/forecasting', label: 'Forecasting' },
  { to: '/settings', label: 'Settings' },
];

interface SidebarProps {
  onClose?: () => void;
}

export default function Sidebar({ onClose }: SidebarProps = {}) {
  const { logout } = useAuth();
  const { dark, toggle } = useTheme();
  return (
    <nav className="w-56 bg-surface border-r border-line flex flex-col py-4 gap-1 h-full">
      <div className="px-4 pb-4 flex items-center justify-between">
        <span className="font-bold text-lg text-blue-700 dark:text-blue-400">CashFlow</span>
        {onClose && (
          <button
            onClick={onClose}
            aria-label="Close menu"
            className="p-1 rounded text-secondary hover:bg-muted-bg md:hidden"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M2 2l12 12M14 2L2 14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        )}
      </div>
      {links.map((l) => (
        <NavLink
          key={l.to}
          to={l.to}
          end={l.to === '/'}
          onClick={onClose}
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
