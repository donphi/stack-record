/**
 * PURPOSE: Fumadocs search endpoint. No custom logic.
 *
 * OWNS:
 *   - GET handler for /api/search
 *
 * TOUCH POINTS:
 *   - lib/source.ts provides source
 *   - Fumadocs search UI calls this endpoint
 */

import { source } from '@/lib/source';
import { createFromSource } from 'fumadocs-core/search/server';

export const { GET } = createFromSource(source, {
  language: 'english',
});
