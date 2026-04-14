/**
 * PURPOSE: MDX component registry: maps Fumadocs + custom components for use in .mdx files.
 *
 * OWNS:
 *   - sharedComponents (merged set of all MDX components available in .mdx without imports)
 *   - getMDXComponents() (used by page renderer to pass components to MDX)
 *   - useMDXComponents (global MDX hook)
 *
 * TOUCH POINTS:
 *   - app/docs/[[...slug]]/page.tsx calls getMDXComponents()
 *   - All .mdx files can use registered components without importing them
 *   - Styling for these components comes from app/global.css and Fumadocs defaults
 */

import defaultMdxComponents from 'fumadocs-ui/mdx';
import type { MDXComponents } from 'mdx/types';
import { Step, Steps } from 'fumadocs-ui/components/steps';
import { Tab, Tabs } from 'fumadocs-ui/components/tabs';
import { Accordion, Accordions } from 'fumadocs-ui/components/accordion';
import { File, Folder, Files } from 'fumadocs-ui/components/files';
import { TypeTable } from 'fumadocs-ui/components/type-table';
import { ImageZoom } from 'fumadocs-ui/components/image-zoom';
import { LibraryTable } from '@/components/library-table';

const sharedComponents: MDXComponents = {
  ...defaultMdxComponents,
  Step,
  Steps,
  Tab,
  Tabs,
  Accordion,
  Accordions,
  File,
  Folder,
  Files,
  TypeTable,
  ImageZoom,
  LibraryTable,
};

export function getMDXComponents(components?: MDXComponents) {
  return {
    ...sharedComponents,
    ...components,
  } satisfies MDXComponents;
}

export const useMDXComponents = getMDXComponents;

declare global {
  type MDXProvidedComponents = ReturnType<typeof getMDXComponents>;
}
