/**
 * PURPOSE: Closure scoring logic: 6-dimension U-L-D-A-E-M scoring.
 *
 * OWNS:
 *   - ClosureBreakdown interface (per-dimension binary scores + total)
 *   - scoreClosure() function (computes closure from BaseNoteMeta)
 *
 * TOUCH POINTS:
 *   - Any future tooling that evaluates note completeness
 *   - maps/open-loops.mdx references closure scores conceptually
 */

import type { BaseNoteMeta } from './note-types';

export interface ClosureBreakdown {
  upward: 0 | 1;
  lateral: 0 | 1;
  downward: 0 | 1;
  applied: 0 | 1;
  epistemic: 0 | 1;
  maintenance: 0 | 1;
  total: number;
}

export function scoreClosure(meta: BaseNoteMeta): ClosureBreakdown {
  const upward: 0 | 1 = meta.parent_maps && meta.parent_maps.length > 0 ? 1 : 0;
  const lateralCount = (meta.related_notes?.length ?? 0) + (meta.prerequisites?.length ?? 0);
  const lateral: 0 | 1 = lateralCount >= 2 ? 1 : 0;
  const downward: 0 | 1 = meta.children && meta.children.length > 0 ? 1 : 0;
  const appliedCount =
    (meta.related_methods?.length ?? 0) +
    (meta.related_systems?.length ?? 0) +
    (meta.related_projects?.length ?? 0);
  const applied: 0 | 1 = appliedCount >= 1 ? 1 : 0;
  const epistemic: 0 | 1 = meta.open_questions && meta.open_questions.length > 0 ? 1 : 0;
  const maintenance: 0 | 1 = meta.review_cycle && meta.last_reviewed ? 1 : 0;
  const total = upward + lateral + downward + applied + epistemic + maintenance;
  return { upward, lateral, downward, applied, epistemic, maintenance, total };
}
