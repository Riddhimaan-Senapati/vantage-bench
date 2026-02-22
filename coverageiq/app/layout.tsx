import type { Metadata } from 'next';
import { Syne, DM_Sans, DM_Mono } from 'next/font/google';
import './globals.css';
import { TooltipProvider } from '@/components/ui/tooltip';
import { Toaster } from '@/components/ui/sonner';
import Sidebar from '@/components/dashboard/Sidebar';
import LoadingScreen from '@/components/LoadingScreen';
import Providers from '@/components/providers';

const syne = Syne({
  subsets: ['latin'],
  weight: ['600', '700', '800'],
  variable: '--font-syne',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  variable: '--font-dm-sans',
});

const dmMono = DM_Mono({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-dm-mono',
});

export const metadata: Metadata = {
  title: 'Vantage',
  description: 'Team coverage intelligence — Vantage',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${syne.variable} ${dmSans.variable} ${dmMono.variable} antialiased bg-bg-base text-foreground`}
      >
        <Providers>
          <LoadingScreen />
          <TooltipProvider delayDuration={300}>
            <div className="flex h-screen overflow-hidden">
              <Sidebar />
              <main className="flex-1 overflow-y-auto">
                {children}
              </main>
            </div>
            <Toaster
              toastOptions={{
                style: {
                  background: 'var(--bg-surface2)',
                  border: '1px solid var(--border)',
                  color: 'var(--foreground)',
                },
              }}
            />
          </TooltipProvider>
        </Providers>
      </body>
    </html>
  );
}
