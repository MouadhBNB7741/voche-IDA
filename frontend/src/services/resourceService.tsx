import { apiClient } from "../lib/apiClient";
import { RESOURCES } from "../lib/api";
import type { Resource } from "../types/db";

export interface ResourceFilters {
  search?: string;
  type?: string;
  category?: string;
  page?: number;
  limit?: number;
}

export interface ResourcesResponse {
  data: Resource[];
  meta: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}

export const resourceService = {
  getAll: async (filters: ResourceFilters = {}): Promise<ResourcesResponse> => {
    const params = new URLSearchParams();
    if (filters.search) params.append("search", filters.search);
    if (filters.type && filters.type !== "all")
      params.append("type", filters.type);
    if (filters.category && filters.category !== "All")
      params.append("category", filters.category);
    if (filters.page) params.append("page", String(filters.page));
    if (filters.limit) params.append("limit", String(filters.limit));

    const response = await apiClient.get<ResourcesResponse>(
      `${RESOURCES.LIST}?${params.toString()}`,
    );
    return response.data;
  },

  // Fetch single resource
  getById: async (id: string): Promise<Resource> => {
    const response = await apiClient.get<Resource>(RESOURCES.DETAILS(id));
    return response.data;
  },

  canAccess: (requiresAuth: boolean, isAuthenticated: boolean): boolean => {
    if (!requiresAuth) return true;
    return isAuthenticated;
  },

  rateResource: async (
    id: string,
    rating: number,
    review?: string,
  ): Promise<{ new_average: number }> => {
    const response = await apiClient.post(RESOURCES.RATE(id), {
      rating,
      review,
    });
    return response.data?.data ?? response.data;
  },

  updateProgress: async (
    id: string,
    progress: number,
    last_position?: string,
  ): Promise<void> => {
    await apiClient.patch(RESOURCES.PROGRESS(id), { progress, last_position });
  },
};

export default resourceService;
