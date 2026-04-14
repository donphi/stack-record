/**
 * PURPOSE: Page-action buttons for LLM-friendly markdown access.
 *
 * OWNS:
 *   - LLMCopyButton (copies page markdown to clipboard)
 *   - ViewOptions (link to view page as plain Markdown)
 *
 * TOUCH POINTS:
 *   - app/docs/[[...slug]]/page.tsx renders these between DocsDescription and DocsBody
 *   - app/llms.mdx/docs/[[...slug]]/route.ts serves the markdown URLs these buttons use
 *
 * SOURCE: Based on `pnpm dlx @fumadocs/cli add ai/page-actions`
 *         (Fumadocs official ai/page-actions pattern)
 */

'use client';

import { Check, Copy, OpenNewWindow } from 'iconoir-react';
import { type ButtonHTMLAttributes, useCallback, useRef, useState } from 'react';

export function LLMCopyButton({ markdownUrl }: { markdownUrl: string }) {
  const [copied, setCopied] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>(null);

  const onCopy = useCallback(async () => {
    try {
      const res = await fetch(markdownUrl);
      const text = await res.text();
      await navigator.clipboard.writeText(text);
      setCopied(true);
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
      timeoutRef.current = setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard write may fail in insecure contexts */
    }
  }, [markdownUrl]);

  return (
    <ActionButton onClick={onCopy} aria-label="Copy Markdown">
      {copied ? (
        <>
          <Check className="size-3.5" strokeWidth={1.6} />
          Copied
        </>
      ) : (
        <>
          <Copy className="size-3.5" strokeWidth={1.6} />
          Copy Markdown
        </>
      )}
    </ActionButton>
  );
}

export function ViewOptions({ markdownUrl }: { markdownUrl: string }) {
  return (
    <a
      href={markdownUrl}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center justify-center gap-2 rounded-md border bg-fd-secondary px-2 py-1.5 text-xs font-medium text-fd-secondary-foreground opacity-50 transition-colors duration-100 hover:opacity-100 hover:bg-fd-accent"
    >
      <OpenNewWindow className="size-3.5" strokeWidth={1.6} />
      View Markdown
    </a>
  );
}

function ActionButton(props: ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      className="inline-flex items-center justify-center gap-2 rounded-md border bg-fd-secondary px-2 py-1.5 text-xs font-medium text-fd-secondary-foreground opacity-50 transition-colors duration-100 hover:opacity-100 hover:bg-fd-accent"
    />
  );
}
