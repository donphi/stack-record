/**
 * PURPOSE: Docs page renderer: MDX body, metadata, TOC.
 *
 * OWNS:
 *   - Individual docs page rendering (MDX body, TOC, breadcrumb, footer)
 *   - Title + description + LLM page-action buttons + border-b divider
 *   - generateStaticParams() for static generation
 *   - generateMetadata() for page-level SEO
 *
 * TOUCH POINTS:
 *   - lib/source.ts provides source.getPage(), source.generateParams()
 *   - components/mdx.tsx provides getMDXComponents()
 *   - components/ai/page-actions.tsx provides LLMCopyButton, ViewOptions
 *   - app/llms.mdx/docs/[[...slug]]/route.ts serves the markdownUrl endpoints
 */

import { source } from '@/lib/source';
import {
  DocsBody,
  DocsDescription,
  DocsPage,
  DocsTitle,
} from 'fumadocs-ui/layouts/docs/page';
import { notFound } from 'next/navigation';
import { getMDXComponents } from '@/components/mdx';
import { createRelativeLink } from 'fumadocs-ui/mdx';
import { LLMCopyButton, ViewOptions } from '@/components/ai/page-actions';
import type { Metadata } from 'next';

export default async function Page(props: {
  params: Promise<{ slug?: string[] }>;
}) {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  const MDX = page.data.body;
  const markdownUrl = `${page.url}.mdx`;

  return (
    <DocsPage toc={page.data.toc} full={page.data.full} tableOfContent={{ style: 'clerk' }}>
      <DocsTitle>{page.data.title}</DocsTitle>
      <DocsDescription>{page.data.description}</DocsDescription>
      <div className="flex w-full flex-row flex-wrap items-center gap-2 pb-6 border-b">
        <LLMCopyButton markdownUrl={markdownUrl} />
        <ViewOptions markdownUrl={markdownUrl} />
      </div>
      <DocsBody>
        <MDX
          components={getMDXComponents({
            a: createRelativeLink(source, page),
          })}
        />
      </DocsBody>
    </DocsPage>
  );
}

export async function generateStaticParams() {
  return source.generateParams();
}

export async function generateMetadata(props: {
  params: Promise<{ slug?: string[] }>;
}): Promise<Metadata> {
  const params = await props.params;
  const page = source.getPage(params.slug);
  if (!page) notFound();

  return {
    title: page.data.title,
    description: page.data.description,
  };
}
