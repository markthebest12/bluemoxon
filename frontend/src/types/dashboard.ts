// Dashboard statistics types for batch endpoint

export interface OverviewStats {
  primary: {
    count: number;
    volumes: number;
    value_low: number;
    value_mid: number;
    value_high: number;
  };
  extended: { count: number };
  flagged: { count: number };
  total_items: number;
  authenticated_bindings: number;
  in_transit: number;
  week_delta: {
    count: number;
    volumes: number;
    value_mid: number;
    authenticated_bindings: number;
  };
}

export interface BinderData {
  binder: string;
  full_name: string;
  count: number;
  value: number;
}

export interface EraData {
  era: string;
  count: number;
  value: number;
}

export interface PublisherData {
  publisher: string;
  tier: string;
  count: number;
  value: number;
  volumes: number;
}

export interface AuthorData {
  author: string;
  count: number;
  value: number;
  volumes: number;
  titles: number;
  sample_titles: string[];
  has_more: boolean;
}

export interface ConditionData {
  condition: string;
  count: number;
  value: number;
}

export interface CategoryData {
  category: string;
  count: number;
  value: number;
}

export interface AcquisitionDay {
  date: string;
  label: string;
  count: number;
  value: number;
  cost: number;
  cumulative_count: number;
  cumulative_value: number;
  cumulative_cost: number;
}

export interface DashboardStats {
  overview: OverviewStats;
  bindings: BinderData[];
  by_era: EraData[];
  by_publisher: PublisherData[];
  by_author: AuthorData[];
  acquisitions_daily: AcquisitionDay[];
  by_condition: ConditionData[];
  by_category: CategoryData[];
}

export interface CachedDashboard {
  version: number;
  data: DashboardStats;
  timestamp: number;
}
