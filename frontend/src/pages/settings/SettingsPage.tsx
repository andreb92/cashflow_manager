import { NavLink, Outlet } from 'react-router-dom';

const tabs = [
  { to: 'payment-methods', label: 'Payment methods' },
  { to: 'categories', label: 'Categories' },
  { to: 'tax-config', label: 'Tax config' },
  { to: 'account', label: 'Account' },
];

export default function SettingsPage() {
  return (
    <div className="max-w-4xl space-y-4">
      <h1 className="text-xl font-bold text-primary">Settings</h1>
      <div className="flex gap-1 border-b border-line">
        {tabs.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) =>
              `px-4 py-2 text-sm border-b-2 -mb-px ${isActive ? 'border-blue-600 text-blue-700 dark:text-blue-400 font-medium' : 'border-transparent text-secondary hover:text-secondary'}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </div>
      <div>
        <Outlet />
      </div>
    </div>
  );
}
