/**
 * PURPOSE: Mobile two-tap folder for sidebar parents that have an index page.
 *
 * OWNS:
 *   - Custom Folder renderer for DocsLayout's sidebar.components slot
 *   - Mobile-only behaviour: first tap on a collapsed folder expands it
 *     without navigating; second tap navigates and lets the drawer auto-close
 *   - Desktop behaviour: identical to vanilla fumadocs-ui
 *
 * TOUCH POINTS:
 *   - app/docs/layout.tsx wires this as sidebar.components.Folder
 *   - Mirrors the default Folder rendering in
 *     fumadocs-ui/components/sidebar/page-tree.js, replacing only the
 *     SidebarFolderLink onClick handler
 *   - Uses only public fumadocs-ui exports (useFolder, useSidebar,
 *     useTreePath, usePathname); no fork, no patch, no CSS
 */

'use client';

import {
  SidebarFolder,
  SidebarFolderContent,
  SidebarFolderLink,
  SidebarFolderTrigger,
  useFolder,
  useSidebar,
} from 'fumadocs-ui/components/sidebar/base';
import { useTreePath } from 'fumadocs-ui/contexts/tree';
import { usePathname } from 'fumadocs-core/framework';
import type * as PageTree from 'fumadocs-core/page-tree';
import type { ReactNode } from 'react';

function isActive(href: string, pathname: string): boolean {
  return pathname === href || pathname.startsWith(href + '/');
}

function TwoTapLink({
  index,
  icon,
  name,
}: {
  index: NonNullable<PageTree.Folder['index']>;
  icon?: ReactNode;
  name: ReactNode;
}) {
  const folder = useFolder();
  const { mode } = useSidebar();
  const pathname = usePathname();
  const active = isActive(index.url, pathname);

  return (
    <SidebarFolderLink
      href={index.url}
      active={active}
      external={index.external}
      onClick={(e) => {
        if (!folder?.collapsible) return;
        const target = e.target as Element;
        const tappedChevron =
          target.matches?.('[data-icon], [data-icon] *') ?? false;

        if (tappedChevron) {
          folder.setOpen(!folder.open);
          e.preventDefault();
          return;
        }

        if (mode === 'drawer' && !folder.open) {
          folder.setOpen(true);
          e.preventDefault();
          return;
        }

        folder.setOpen(active ? !folder.open : true);
      }}
    >
      {icon}
      {name}
    </SidebarFolderLink>
  );
}

export function TwoTapFolder({
  item,
  children,
}: {
  item: PageTree.Folder;
  children: ReactNode;
}) {
  const path = useTreePath();
  return (
    <SidebarFolder
      collapsible={item.collapsible}
      active={path.includes(item)}
      defaultOpen={item.defaultOpen}
    >
      {item.index ? (
        <TwoTapLink index={item.index} icon={item.icon} name={item.name} />
      ) : (
        <SidebarFolderTrigger>
          {item.icon}
          {item.name}
        </SidebarFolderTrigger>
      )}
      <SidebarFolderContent>{children}</SidebarFolderContent>
    </SidebarFolder>
  );
}
