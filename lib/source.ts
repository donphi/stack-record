/**
 * PURPOSE: Fumadocs content loader and icon resolver.
 *
 * OWNS:
 *   - NAV_STROKE (sidebar icon stroke weight — React prop, not CSS)
 *   - source (Fumadocs loader instance, baseUrl: /docs)
 *
 * TOUCH POINTS:
 *   - app/docs/layout.tsx reads source.getPageTree()
 *   - app/docs/[[...slug]]/page.tsx reads source.getPage(), source.generateParams()
 *   - app/api/search/route.ts reads source
 */

import { docs } from 'collections/server';
import { loader } from 'fumadocs-core/source';
import * as IconoirIcons from 'iconoir-react';
import type { SVGProps } from 'react';
import { createElement, type FC } from 'react';

type SvgIcon = FC<SVGProps<SVGSVGElement>>;
const icons = IconoirIcons as unknown as Record<string, SvgIcon>;

const NAV_STROKE = 1.4;

export const source = loader({
  baseUrl: '/docs',
  source: docs.toFumadocsSource(),
  icon(name: string | undefined) {
    if (!name) return;
    const Icon = icons[name];
    if (Icon) return createElement(Icon, { strokeWidth: NAV_STROKE });
  },
});
