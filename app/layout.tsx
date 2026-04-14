/**
 * PURPOSE: Root HTML shell: fonts (next/font), RootProvider, KaTeX CSS.
 *
 * OWNS:
 *   - Font loading (Plus Jakarta Sans, JetBrains Mono via next/font)
 *   - CSS variable injection (--font-pjs, --font-jbm on <html>)
 *   - KaTeX stylesheet import
 *   - NewCMMath font override for KaTeX (loaded in global.css, files in public/fonts/)
 *   - RootProvider wrapper (Fumadocs theme provider)
 *
 * TOUCH POINTS:
 *   - app/global.css reads --font-pjs and --font-jbm via @theme
 *   - All child routes inherit this shell
 */

import { RootProvider } from 'fumadocs-ui/provider/next';
import type { ReactNode } from 'react';
import { Plus_Jakarta_Sans, JetBrains_Mono } from 'next/font/google';
import 'katex/dist/katex.css';
import './global.css';

const sans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-pjs',
});

const mono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-jbm',
});

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${sans.variable} ${mono.variable}`}
      suppressHydrationWarning
    >
      <body className="flex flex-col min-h-screen font-sans">
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
