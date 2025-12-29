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
  id: number;
  name: string;
  tier: string | null;
  preferred: boolean;
  book_count: number;
}

// Extended entity types for forms
export interface AuthorEntity extends EntityTier {
  birth_year?: number | null;
  death_year?: number | null;
  era?: string | null;
  first_acquired_date?: string | null;
  priority_score?: number;
}

export interface PublisherEntity extends EntityTier {
  founded_year?: number | null;
  description?: string | null;
}

export interface BinderEntity extends EntityTier {
  full_name?: string | null;
  authentication_markers?: string | null;
}

export interface ReassignRequest {
  target_id: number;
}

export interface ReassignResponse {
  reassigned_count: number;
  deleted_entity: string;
  target_entity: string;
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

export interface InfrastructureConfig {
  aws_region: string;
  images_bucket: string;
  backup_bucket: string;
  images_cdn_url?: string;
  analysis_queue?: string;
  eval_runbook_queue?: string;
}

export interface LimitsConfig {
  bedrock_read_timeout_sec: number;
  bedrock_connect_timeout_sec: number;
  image_max_bytes: number;
  image_safe_bytes: number;
  prompt_cache_ttl_sec: number;
  presigned_url_expiry_sec: number;
}

export interface SystemInfoResponse {
  is_cold_start: boolean;
  timestamp: string;
  system: SystemInfo;
  health: HealthInfo;
  models: Record<string, ModelInfo>;
  infrastructure: InfrastructureConfig;
  limits: LimitsConfig;
  scoring_config: ScoringConfig;
  entity_tiers: EntityTiers;
}

export interface BedrockModelCost {
  model_name: string;
  usage: string;
  mtd_cost: number;
}

export interface DailyCost {
  date: string;
  cost: number;
}

export interface CostResponse {
  period_start: string;
  period_end: string;
  bedrock_models: BedrockModelCost[];
  bedrock_total: number;
  daily_trend: DailyCost[];
  other_costs: Record<string, number>;
  total_aws_cost: number;
  cached_at: string;
  error?: string;
}
