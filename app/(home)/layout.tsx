/**
 * PURPOSE: Landing page shell: HomeLayout with shared nav options.
 *
 * OWNS:
 *   - HomeLayout wrapper for the / route
 *
 * TOUCH POINTS:
 *   - lib/layout.shared.tsx provides baseOptions()
 *   - app/(home)/page.tsx renders inside this layout
 */

import type { ReactNode } from 'react';
import { HomeLayout } from 'fumadocs-ui/layouts/home';
import { baseOptions } from '@/lib/layout.shared';

export default function Layout({ children }: { children: ReactNode }) {
  return <HomeLayout {...baseOptions()}>{children}</HomeLayout>;
}
