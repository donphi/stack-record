/**
 * PURPOSE: Knowledge graph type definitions: NoteType, ClosureStatus, ReviewCycle, BaseNoteMeta.
 *
 * OWNS:
 *   - NoteType enum (9 values)
 *   - ClosureStatus enum (4 values)
 *   - ReviewCycle enum (5 values)
 *   - BaseNoteMeta interface (all sidecar fields)
 *
 * TOUCH POINTS:
 *   - lib/closure.ts imports BaseNoteMeta for scoreClosure()
 *   - scripts/materialize-fumadocs.ts validates against these types conceptually
 *   - content-src/docs/**\/*.meta.json must conform to BaseNoteMeta shape
 */

export type NoteType =
  | 'map' | 'concept' | 'method' | 'system'
  | 'decision' | 'experiment' | 'project'
  | 'standard' | 'reference';

export type ClosureStatus = 'open' | 'partial' | 'closed' | 'archived';
export type ReviewCycle = 'weekly' | 'monthly' | 'quarterly' | 'yearly' | 'never';

export interface BaseNoteMeta {
  title: string;
  description: string;
  id: string;
  type: NoteType;
  domain?: string;
  status?: string;
  tags?: string[];
  aliases?: string[];
  icon?: string;
  parent_maps?: string[];
  prerequisites?: string[];
  children?: string[];
  related_notes?: string[];
  related_methods?: string[];
  related_systems?: string[];
  related_projects?: string[];
  related_experiments?: string[];
  related_decisions?: string[];
  related_standards?: string[];
  review_cycle?: ReviewCycle;
  last_reviewed?: string;
  closure_score?: number;
  closure_status?: ClosureStatus;
  open_questions?: string[];
  superseded_by?: string[];
  supersedes?: string[];
  blocked_by?: string[];
  // Method-specific
  uses_concepts?: string[];
  implemented_in?: string[];
  validated_by?: string[];
  // System-specific
  implements_methods?: string[];
  depends_on?: string[];
  used_in_projects?: string[];
  // Decision-specific
  decision_status?: string;
  date_decided?: string;
  deciders?: string[];
  alternatives?: string[];
  // Experiment-specific
  date_started?: string;
  date_completed?: string;
  // Project-specific
  key_methods?: string[];
  key_systems?: string[];
  key_decisions?: string[];
}
