import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useMemo } from 'react';
import { AuthProvider } from './contexts/AuthContext';
import { createRouter } from './router';

export default function App() {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 60 * 1000, retry: 1 } },
      }),
    []
  );

  const router = useMemo(() => createRouter(), []);

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <RouterProvider router={router} />
      </AuthProvider>
    </QueryClientProvider>
  );
}
