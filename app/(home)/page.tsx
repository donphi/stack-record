/**
 * PURPOSE: Landing page content.
 *
 * OWNS:
 *   - / route content (hero text + link to docs)
 *
 * TOUCH POINTS:
 *   - app/(home)/layout.tsx wraps this in HomeLayout
 */

import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex flex-1 flex-col items-center justify-center text-center px-4">
      <h1 className="text-4xl font-bold mb-4">Stack Record</h1>
      <p className="text-lg text-muted-foreground mb-8">
        Long-horizon learning system for concepts, methods, systems, decisions, and projects.
      </p>
      <Link
        href="/docs"
        className="rounded-lg bg-primary px-6 py-3 text-primary-foreground font-medium hover:bg-primary/90 transition-colors"
      >
        Open Docs
      </Link>
    </main>
  );
}
