import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="flex h-screen">
      {/* Desktop sidebar — hidden on mobile */}
      <div className="hidden md:flex shrink-0">
        <Sidebar />
      </div>

      {/* Mobile overlay drawer */}
      {menuOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/50"
            onClick={() => setMenuOpen(false)}
          />
          {/* Drawer */}
          <div className="relative z-50 h-full w-64 bg-surface shadow-xl">
            <Sidebar onClose={() => setMenuOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content column */}
      <div className="flex flex-col flex-1 min-w-0">
        {/* Mobile top bar — hidden on desktop */}
        <header className="md:hidden flex items-center justify-between px-4 h-14 bg-surface border-b border-line shrink-0">
          <span className="font-bold text-blue-700 dark:text-blue-400">CashFlow</span>
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Open navigation menu"
            className="p-2 rounded text-secondary hover:bg-muted-bg transition-colors"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
              <rect y="3" width="20" height="2" rx="1"/>
              <rect y="9" width="20" height="2" rx="1"/>
              <rect y="15" width="20" height="2" rx="1"/>
            </svg>
          </button>
        </header>

        <main className="flex-1 overflow-auto bg-canvas p-4 md:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
