/**
 * PURPOSE: Shared layout options: site title, nav config.
 *
 * OWNS:
 *   - baseOptions() — site title and nav configuration shared by all layouts
 *
 * TOUCH POINTS:
 *   - app/docs/layout.tsx spreads baseOptions() into DocsLayout
 *   - app/(home)/layout.tsx spreads baseOptions() into HomeLayout
 */

import type { BaseLayoutProps } from 'fumadocs-ui/layouts/shared';

export function baseOptions(): BaseLayoutProps {
  return {
    nav: {
      title: 'Stack Record',
    },
    githubUrl: 'https://github.com/your-username/stack-record',
  };
}
