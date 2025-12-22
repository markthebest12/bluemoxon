export interface HealthCheck {
  status: string;
  latency_ms?: number;
  error?: string;
  book_count?: number;
  bucket?: string;
  user_pool?: string;
  reason?: string;
}

export interface HealthInfo {
  overall: string;
  total_latency_ms: number;
  checks: {
    database: HealthCheck;
    s3: HealthCheck;
    cognito: HealthCheck;
  };
}

export interface SystemInfo {
  version: string;
  git_sha?: string;
  deploy_time?: string;
  environment: string;
}

export interface EntityTier {
  name: string;
  tier: string;
}

export interface EntityTiers {
  authors: EntityTier[];
  publishers: EntityTier[];
  binders: EntityTier[];
}

export interface ScoringConfig {
  quality_points: Record<string, number>;
  strategic_points: Record<string, number>;
  thresholds: Record<string, number>;
  weights: Record<string, number>;
  offer_discounts: Record<string, number>;
  era_boundaries: Record<string, number>;
}

export interface ModelInfo {
  model_id: string;
  usage: string;
}

export interface SystemInfoResponse {
  is_cold_start: boolean;
  timestamp: string;
  system: SystemInfo;
  health: HealthInfo;
  models: Record<string, ModelInfo>;
  scoring_config: ScoringConfig;
  entity_tiers: EntityTiers;
}
