/**
 * PURPOSE: Docs shell: DocsLayout + page tree. No custom logic.
 *
 * OWNS:
 *   - DocsLayout wrapper for all /docs/** routes
 *   - Page tree injection from source.getPageTree()
 *
 * TOUCH POINTS:
 *   - lib/source.ts provides source.getPageTree()
 *   - lib/layout.shared.tsx provides baseOptions()
 *   - app/docs/[[...slug]]/page.tsx renders inside this layout
 */

import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';
import type { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout tree={source.getPageTree()} {...baseOptions()}>
      {children}
    </DocsLayout>
  );
}
