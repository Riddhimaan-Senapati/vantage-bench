'use client';

import { usePathname } from 'next/navigation';
import Sidebar from '@/components/dashboard/Sidebar';
import LoadingScreen from '@/components/LoadingScreen';
import { TooltipProvider } from '@/components/ui/tooltip';

export default function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname?.startsWith('/sign-in');

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <TooltipProvider delayDuration={300}>
      <LoadingScreen />
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </TooltipProvider>
  );
}
