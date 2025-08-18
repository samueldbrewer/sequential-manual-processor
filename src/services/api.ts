import axios from 'axios';
import { Manufacturer, Model, Manual, HealthResponse, ApiResponse } from '../types';

// Use relative URL when deployed (same domain), absolute URL for local development
const API_BASE_URL = process.env.REACT_APP_API_URL || 
  (window.location.hostname === 'localhost' ? 'http://localhost:8888' : '');

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds timeout (increased for browser creation)
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Include cookies for session management
});

// Simple cache to prevent duplicate requests (without StrictMode, this is less critical)
const requestCache = new Map<string, { data: any, timestamp: number }>();
const CACHE_DURATION = 10000; // 10 seconds cache to prevent duplicate requests

const api = {
  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  },
  
  async clearSessionPdfs(): Promise<void> {
    await apiClient.post('/api/clear-session-pdfs');
  },

  async getManufacturers(search?: string, limit?: number): Promise<Manufacturer[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (limit) params.append('limit', limit.toString());
    
    const url = `/api/manufacturers${params.toString() ? '?' + params.toString() : ''}`;
    
    // Simple direct call
    const response = await apiClient.get<ApiResponse<Manufacturer[]>>(url);
    
    if (response.data.success) {
      return response.data.data;
    }
    throw new Error(response.data.error || 'Failed to fetch manufacturers');
  },

  async getModels(manufacturerId: string, search?: string, limit?: number): Promise<Model[]> {
    const params = new URLSearchParams();
    if (search) params.append('search', search);
    if (limit) params.append('limit', limit.toString());
    
    const url = `/api/manufacturers/${manufacturerId}/models${params.toString() ? '?' + params.toString() : ''}`;
    
    // Check simple cache first
    const cached = requestCache.get(url);
    if (cached && Date.now() - cached.timestamp < CACHE_DURATION) {
      console.log(`📦 Using cached models for: ${manufacturerId} (age: ${Date.now() - cached.timestamp}ms)`);
      return cached.data;
    }
    
    // Direct API call
    console.log(`🔄 Making API request for models: ${manufacturerId}`);
    const response = await apiClient.get<ApiResponse<Model[]>>(url);
    
    if (response.data.success) {
      // Cache the result for longer
      requestCache.set(url, { data: response.data.data, timestamp: Date.now() });
      console.log(`✅ Cached ${response.data.data.length} models for ${manufacturerId}`);
      return response.data.data;
    }
    throw new Error(response.data.error || 'Failed to fetch models');
  },

  async getManuals(manufacturerId: string, modelId: string): Promise<Manual[]> {
    const response = await apiClient.get<ApiResponse<Manual[]>>(
      `/api/manufacturers/${manufacturerId}/models/${modelId}/manuals`
    );
    
    if (response.data.success) {
      return response.data.data;
    }
    throw new Error(response.data.error || 'Failed to fetch manuals');
  },

  async processManual(manualUrl: string): Promise<any> {
    const response = await apiClient.post('/api/process-manual', {
      manualUrl
    });
    
    return response.data;
  }
};

export default api;