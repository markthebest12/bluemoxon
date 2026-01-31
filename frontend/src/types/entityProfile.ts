/**
 * Entity Profile types.
 * Maps to backend EntityProfileResponse schema.
 */

import type { NodeType, Era, Tier } from "@/types/socialCircles";

// === Gossip Types ===

export type Significance = "revelation" | "notable" | "context";
export type Tone = "dramatic" | "scandalous" | "tragic" | "intellectual" | "triumphant";
export type DisplayLocation = "hero-bio" | "timeline" | "hover-tooltip" | "connection-detail";
export type NarrativeStyle = "prose-paragraph" | "bullet-facts" | "timeline-events";
export type NarrativeTrigger =
  | "cross_era_bridge"
  | "social_circle"
  | "hub_figure"
  | "influence_chain"
  | null;

export interface BiographicalFact {
  text: string;
  year?: number;
  significance: Significance;
  tone: Tone;
  display_in: DisplayLocation[];
}

export interface RelationshipNarrative {
  summary: string;
  details: BiographicalFact[];
  narrative_style: NarrativeStyle;
}

// === Profile Response Types ===

export interface ProfileEntity {
  id: number;
  type: NodeType;
  name: string;
  birth_year?: number;
  death_year?: number;
  founded_year?: number;
  closed_year?: number;
  era?: Era;
  tier?: Tier;
}

export interface ProfileData {
  bio_summary: string | null;
  personal_stories: BiographicalFact[];
  is_stale: boolean;
  generated_at: string | null;
  model_version: string | null;
}

export interface ProfileConnection {
  entity: ProfileEntity;
  connection_type: string;
  strength: number;
  shared_book_count: number;
  shared_books: ProfileBook[];
  narrative: string | null;
  narrative_trigger: NarrativeTrigger;
  is_key: boolean;
  relationship_story: RelationshipNarrative | null;
}

export interface ProfileBook {
  id: number;
  title: string;
  year?: number;
  condition?: string;
  edition?: string;
}

export interface ProfileStats {
  total_books: number;
  total_estimated_value: number | null;
  first_editions: number;
  date_range: number[];
}

export interface EntityProfileResponse {
  entity: ProfileEntity;
  profile: ProfileData;
  connections: ProfileConnection[];
  books: ProfileBook[];
  stats: ProfileStats;
}
