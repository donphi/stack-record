/**
 * PURPOSE: Fumadocs MDX config: content directory, remark/rehype plugins.
 *
 * OWNS:
 *   - docs collection definition (dir: .generated/docs, includes both doc + meta collections)
 *   - MDX plugin pipeline (remark-math, rehype-katex)
 *   - includeProcessedMarkdown (enables getText('processed') for LLM endpoints)
 *
 * TOUCH POINTS:
 *   - lib/source.ts imports docs via 'collections/server'
 *   - scripts/materialize-fumadocs.ts writes to .generated/docs (this file reads from it)
 *   - app/layout.tsx imports katex CSS for the styles these plugins need
 *   - lib/get-llm-text.ts calls page.data.getText('processed') (requires includeProcessedMarkdown)
 */

import { defineDocs, defineConfig } from 'fumadocs-mdx/config';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export const docs = defineDocs({
  dir: '.generated/docs',
  docs: {
    postprocess: {
      includeProcessedMarkdown: true,
    },
  },
});

export default defineConfig({
  mdxOptions: {
    remarkPlugins: [remarkMath],
    rehypePlugins: (v) => [rehypeKatex, ...v],
  },
});
