/**
 * PURPOSE: Sidecar materialiser: joins content-src/ body + .meta.json into .generated/ with frontmatter.
 *
 * OWNS:
 *   - SRC_DIR (content-src/docs) — where authored body + sidecar pairs live
 *   - OUT_DIR (.generated/docs) — build artifact consumed by Fumadocs
 *   - Pairing validation (every .mdx ↔ .meta.json)
 *   - Required-field validation (title, description, id, type)
 *   - Frontmatter-in-source rejection
 *   - Wiki-link resolution ([[name]] → standard markdown links in generated output)
 *
 * TOUCH POINTS:
 *   - package.json "docs:materialize" script runs this
 *   - source.config.ts reads from OUT_DIR (.generated/docs)
 *   - content-src/docs/ is the input tree
 */

import fs from 'node:fs/promises';
import path from 'node:path';
import matter from 'gray-matter';
import type { NoteType } from '../lib/note-types';

const SRC_DIR = path.resolve('content-src/docs');
const OUT_DIR = path.resolve('.generated/docs');

const VALID_NOTE_TYPES: readonly string[] = [
  'map', 'concept', 'method', 'system',
  'decision', 'experiment', 'project',
  'standard', 'reference',
] satisfies readonly NoteType[];

async function rmrf(dir: string): Promise<void> {
  await fs.rm(dir, { recursive: true, force: true });
}

async function ensureDir(dir: string): Promise<void> {
  await fs.mkdir(dir, { recursive: true });
}

async function listFilesRecursive(dir: string): Promise<string[]> {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const out: string[] = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...(await listFilesRecursive(full)));
    } else {
      out.push(full);
    }
  }
  return out;
}

function isPageBodyFile(file: string): boolean {
  return file.endsWith('.mdx');
}

function isFolderMetaFile(file: string): boolean {
  return path.basename(file) === 'meta.json';
}

function isPageMetaFile(file: string): boolean {
  return file.endsWith('.meta.json') && path.basename(file) !== 'meta.json';
}

function toPosix(p: string): string {
  return p.split(path.sep).join('/');
}

function relativeFromSrc(file: string): string {
  return toPosix(path.relative(SRC_DIR, file));
}

function parsePageMeta(raw: unknown, file: string): Record<string, unknown> {
  if (!raw || typeof raw !== 'object') {
    throw new Error(`Invalid page meta object: ${file}`);
  }
  const obj = raw as Record<string, unknown>;
  const requiredStrings = ['title', 'description', 'id', 'type'] as const;
  for (const key of requiredStrings) {
    if (typeof obj[key] !== 'string' || (obj[key] as string).trim() === '') {
      throw new Error(`Missing required "${key}" in ${file}`);
    }
  }
  if (!VALID_NOTE_TYPES.includes(obj['type'] as string)) {
    throw new Error(
      `Invalid type "${obj['type']}" in ${file}. ` +
      `Must be one of: ${VALID_NOTE_TYPES.join(', ')}`
    );
  }
  return obj;
}

function expectedPageMetaPath(docFile: string): string {
  const ext = path.extname(docFile);
  return docFile.slice(0, -ext.length) + '.meta.json';
}

function outputPathForSourceFile(srcFile: string): string {
  const rel = path.relative(SRC_DIR, srcFile);
  if (isPageMetaFile(srcFile)) {
    throw new Error(`Page meta sidecars are not copied directly: ${srcFile}`);
  }
  return path.join(OUT_DIR, rel);
}

const BASE_URL = '/docs';

interface WikiTarget {
  title: string;
  url: string;
}

function slugFromMetaPath(metaFile: string): string {
  const rel = toPosix(path.relative(SRC_DIR, metaFile));
  const withoutExt = rel.replace(/\.meta\.json$/, '');
  if (withoutExt.endsWith('/index') || withoutExt === 'index') {
    const dir = withoutExt.replace(/\/?index$/, '');
    return dir === '' ? '' : dir;
  }
  return withoutExt;
}

function toWikiKey(slug: string): string {
  const last = slug.split('/').pop() ?? slug;
  return last.replace(/-/g, '_').toLowerCase();
}

function camelToKebab(name: string): string {
  return name
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase();
}

function normalizeWikiName(raw: string): string {
  if (/[a-z]/.test(raw) && /[A-Z]/.test(raw) && !raw.includes('_')) {
    return camelToKebab(raw).replace(/-/g, '_').toLowerCase();
  }
  return raw.replace(/-/g, '_').toLowerCase();
}

function wikiDisplayName(raw: string): string {
  return raw.replace(/_/g, ' ');
}

async function buildWikiLinkMap(
  pageMetas: string[],
): Promise<Map<string, WikiTarget>> {
  const map = new Map<string, WikiTarget>();

  for (const metaFile of pageMetas) {
    const raw = await fs.readFile(metaFile, 'utf8');
    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      continue;
    }
    const title = typeof parsed['title'] === 'string' ? parsed['title'] : '';
    if (!title) continue;

    const slug = slugFromMetaPath(metaFile);
    const url = slug === '' ? BASE_URL : `${BASE_URL}/${slug}`;
    const key = toWikiKey(slug);

    if (key && !map.has(key)) {
      map.set(key, { title, url });
    }

    const kebabSlug = slug.split('/').pop() ?? '';
    const camelKey = camelToKebab(kebabSlug).replace(/-/g, '_').toLowerCase();
    if (camelKey && camelKey !== key && !map.has(camelKey)) {
      map.set(camelKey, { title, url });
    }
  }

  return map;
}

const unresolvedWikiLinks = new Set<string>();

function resolveWikiLinks(
  body: string,
  wikiMap: Map<string, WikiTarget>,
): string {
  return body.replace(/\[\[([^\]]+)\]\]/g, (_match, rawName: string) => {
    const normalized = normalizeWikiName(rawName);
    const target = wikiMap.get(normalized);
    if (target) {
      return `[${target.title}](${target.url})`;
    }
    unresolvedWikiLinks.add(rawName);
    return wikiDisplayName(rawName);
  });
}

async function copyFolderMeta(file: string): Promise<void> {
  const out = outputPathForSourceFile(file);
  await ensureDir(path.dirname(out));
  await fs.copyFile(file, out);
}

async function materializePage(
  docFile: string,
  wikiMap: Map<string, WikiTarget>,
): Promise<void> {
  const metaFile = expectedPageMetaPath(docFile);
  try {
    await fs.access(metaFile);
  } catch {
    throw new Error(
      `Missing sidecar meta file for page body:\n` +
      `  body: ${relativeFromSrc(docFile)}\n` +
      `  expected meta: ${relativeFromSrc(metaFile)}`
    );
  }
  const [body, metaRaw] = await Promise.all([
    fs.readFile(docFile, 'utf8'),
    fs.readFile(metaFile, 'utf8'),
  ]);
  if (body.trimStart().startsWith('---')) {
    throw new Error(`Authored body file must not contain frontmatter: ${relativeFromSrc(docFile)}`);
  }
  const parsedMeta = parsePageMeta(JSON.parse(metaRaw), relativeFromSrc(metaFile));
  const resolved = resolveWikiLinks(body.trimStart(), wikiMap);
  const compiled = matter.stringify(resolved, parsedMeta);
  const out = outputPathForSourceFile(docFile);
  await ensureDir(path.dirname(out));
  await fs.writeFile(out, compiled, 'utf8');
}

async function main(): Promise<void> {
  await rmrf(OUT_DIR);
  await ensureDir(OUT_DIR);
  const files = await listFilesRecursive(SRC_DIR);
  const docs = files.filter(isPageBodyFile);
  const folderMetas = files.filter(isFolderMetaFile);
  const pageMetas = files.filter(isPageMetaFile);

  for (const metaFile of pageMetas) {
    const possibleMdx = metaFile.replace(/\.meta\.json$/, '.mdx');
    const hasBody = files.includes(possibleMdx);
    if (!hasBody) {
      throw new Error(`Orphan page meta file without matching body:\n  ${relativeFromSrc(metaFile)}`);
    }
  }

  const wikiMap = await buildWikiLinkMap(pageMetas);

  for (const file of folderMetas) {
    await copyFolderMeta(file);
  }
  for (const docFile of docs) {
    await materializePage(docFile, wikiMap);
  }

  console.log(`Materialized ${docs.length} page(s) into ${OUT_DIR}`);

  if (unresolvedWikiLinks.size > 0) {
    const sorted = [...unresolvedWikiLinks].sort();
    console.warn(
      `Warning: ${sorted.length} unresolved wiki-link(s): ${sorted.join(', ')}`
    );
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
