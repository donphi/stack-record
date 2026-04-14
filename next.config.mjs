/**
 * PURPOSE: Next.js config: standalone output, createMDX wrapper, LLM rewrite.
 *
 * OWNS:
 *   - Next.js build settings (reactStrictMode, standalone output)
 *   - createMDX integration (Fumadocs MDX pipeline)
 *   - Rewrite: /docs/:path*.mdx → /llms.mdx/docs/:path* (LLM markdown endpoints)
 *
 * TOUCH POINTS:
 *   - Dockerfile reads standalone output from .next/standalone
 *   - source.config.ts defines the MDX plugin pipeline wrapped by createMDX
 *   - app/llms.mdx/docs/[[...slug]]/route.ts handles the rewritten requests
 */

import { createMDX } from 'fumadocs-mdx/next';

/** @type {import('next').NextConfig} */
const config = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/docs/:path*.mdx',
        destination: '/llms.mdx/docs/:path*',
      },
    ];
  },
};

const withMDX = createMDX();

export default withMDX(config);
