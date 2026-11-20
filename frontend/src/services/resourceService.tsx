import { apiClient } from "../lib/apiClient";
import { RESOURCES } from "../lib/api";
import type { Resource } from "../types/db";

export interface ResourceFilters {
  search?: string;
  type?: string;
  category?: string;
  page?: number;
  limit?: number;
  sort?: string;
  language?: string;
  featured?: boolean;
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
    if (filters.sort) params.append("sort", filters.sort);
    if (filters.page) params.append("page", String(filters.page));
    if (filters.limit) params.append("limit", String(filters.limit));
    if (filters.language && filters.language !== "All")
      params.append("language", filters.language);
    if (filters.featured !== undefined && filters.featured !== null)
      params.append("featured", String(filters.featured));

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

  // ── Sharing resources ────────────────────────────────────────────────
  canSubmit: async (): Promise<{ can_submit: boolean; reason?: string | null }> => {
    const response = await apiClient.get(RESOURCES.CAN_SUBMIT);
    return response.data;
  },

  /** Sends the form as multipart: the file (if any) and the text fields. */
  submit: async (form: FormData): Promise<Resource> => {
    const response = await apiClient.post<Resource>(RESOURCES.SUBMIT, form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  getMine: async (): Promise<ResourcesResponse> => {
    const response = await apiClient.get<ResourcesResponse>(RESOURCES.MINE);
    return response.data;
  },

  /** Counts the download and says whether the resource is an uploaded file or a link. */
  getDownload: async (
    id: string,
  ): Promise<{ has_file: boolean; download_url?: string | null; file_name?: string | null }> => {
    const response = await apiClient.get(RESOURCES.DOWNLOAD(id));
    return response.data;
  },

  /** The uploaded file, fetched with the user's login so resources that need sign-in work too. */
  getFile: async (id: string): Promise<Blob> => {
    const response = await apiClient.get(RESOURCES.FILE(id), { responseType: "blob" });
    return response.data;
  },
};

export default resourceService;
