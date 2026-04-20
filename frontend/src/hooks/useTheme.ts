import { useEffect, useState } from 'react';

function readStoredTheme() {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem('theme');
  } catch {
    return null;
  }
}

function writeStoredTheme(value: 'dark' | 'light') {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem('theme', value);
  } catch {
    // Ignore storage failures in restricted test or browser environments.
  }
}

export function useTheme() {
  const [dark, setDark] = useState(() => {
    if (typeof window === 'undefined') return false;
    const stored = readStoredTheme();
    if (stored) return stored === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
    writeStoredTheme(dark ? 'dark' : 'light');
  }, [dark]);

  return { dark, toggle: () => setDark((d) => !d) };
}
