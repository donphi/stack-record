/**
 * PURPOSE: Docs shell: DocsLayout + page tree, with mobile two-tap folder override.
 *
 * OWNS:
 *   - DocsLayout wrapper for all /docs/** routes
 *   - Page tree injection from source.getPageTree()
 *   - sidebar.components.Folder override for mobile two-tap behaviour
 *     (first tap on a collapsed folder expands; second tap navigates)
 *
 * TOUCH POINTS:
 *   - lib/source.ts provides source.getPageTree()
 *   - lib/layout.shared.tsx provides baseOptions()
 *   - components/sidebar/two-tap-folder.tsx provides TwoTapFolder
 *   - app/docs/[[...slug]]/page.tsx renders inside this layout
 */

import { source } from '@/lib/source';
import { DocsLayout } from 'fumadocs-ui/layouts/docs';
import { baseOptions } from '@/lib/layout.shared';
import { TwoTapFolder } from '@/components/sidebar/two-tap-folder';
import type { ReactNode } from 'react';

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <DocsLayout
      tree={source.getPageTree()}
      sidebar={{ components: { Folder: TwoTapFolder } }}
      {...baseOptions()}
    >
      {children}
    </DocsLayout>
  );
}
