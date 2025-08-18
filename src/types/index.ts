export interface Manufacturer {
  id: string;
  name: string;
  uri: string;
  modelCount: number;
}

export interface Model {
  id: string;
  name: string;
  description?: string;
  url?: string;
  manualCount?: number;
  manuals?: Manual[];
}

export interface Manual {
  type: string;
  title: string;
  url: string;
  full_url?: string;
  language?: string;
  format?: string;
}

export interface HealthResponse {
  status: string;
  scraper_ready: boolean;
  timestamp: string;
  cache_status?: {
    manufacturers_cached: boolean;
    models_cached: number;
    cache_age: number;
  };
}

export interface ApiResponse<T> {
  success: boolean;
  count?: number;
  data: T;
  error?: string;
}