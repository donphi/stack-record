/**
 * PURPOSE: Serves page content as plain Markdown when *.mdx is appended to a docs URL.
 *
 * OWNS:
 *   - GET handler returning text/markdown for any docs page
 *   - generateStaticParams() for static generation of all markdown endpoints
 *   - revalidate = false (cached forever)
 *
 * TOUCH POINTS:
 *   - next.config.mjs rewrites /docs/:path*.mdx to this route
 *   - lib/get-llm-text.ts provides getLLMText()
 *   - lib/source.ts provides source.getPage(), source.generateParams()
 *   - components/ai/page-actions.tsx buttons link to URLs served by this handler
 */

import { getLLMText } from '@/lib/get-llm-text';
import { source } from '@/lib/source';
import { notFound } from 'next/navigation';

export const revalidate = false;

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug?: string[] }> },
) {
  const { slug } = await params;
  const page = source.getPage(slug);
  if (!page) notFound();

  return new Response(await getLLMText(page), {
    headers: { 'Content-Type': 'text/markdown' },
  });
}

export function generateStaticParams() {
  return source.generateParams();
}
