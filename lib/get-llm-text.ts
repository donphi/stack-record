/**
 * PURPOSE: Converts a Fumadocs page into plain Markdown text for LLM consumption.
 *
 * OWNS:
 *   - getLLMText() — returns processed Markdown with title and URL header
 *
 * TOUCH POINTS:
 *   - app/llms.mdx/docs/[[...slug]]/route.ts calls getLLMText() to serve *.mdx responses
 *   - source.config.ts must have includeProcessedMarkdown enabled
 *   - lib/source.ts provides the source type used by InferPageType
 */

import { source } from '@/lib/source';
import type { InferPageType } from 'fumadocs-core/source';

export async function getLLMText(
  page: InferPageType<typeof source>,
): Promise<string> {
  const processed = await page.data.getText('processed');

  return `# ${page.data.title} (${page.url})\n\n${processed}`;
}
