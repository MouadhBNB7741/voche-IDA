import type { Resource } from '../types/db';

/**
 * Voche Resource Service
 * Standardized for backend API integration.
 * Static mock data removed.
 */

export interface ExtendedResource extends Resource {
  // Add any frontend-specific fields if needed, 
  // but db.ts now covers featured, requires_auth, etc.
}

export const platformResources: ExtendedResource[] = [];

export const resourceService = {
  getAll(): ExtendedResource[] {
    return platformResources;
  },

  getById(id: string): ExtendedResource | undefined {
    return platformResources.find(resource => resource.resource_id === id);
  },

  getFeatured(): ExtendedResource[] {
    return platformResources.filter(resource => resource.featured);
  },

  search(query: string, filters?: { type?: string; category?: string }): ExtendedResource[] {
    return platformResources.filter(resource => {
      const matchesSearch = !query ||
        resource.title.toLowerCase().includes(query.toLowerCase()) ||
        resource.description.toLowerCase().includes(query.toLowerCase());
      
      const matchesType = !filters?.type || filters.type === 'all' || resource.type === filters.type;
      const matchesCategory = !filters?.category || filters.category === 'All' || resource.category === filters.category;
      
      return matchesSearch && matchesType && matchesCategory;
    });
  },

  canAccess(resourceId: string, isAuthenticated: boolean): boolean {
    const resource = this.getById(resourceId);
    if (!resource) return false;
    if (!resource.requires_auth) return true;
    return isAuthenticated;
  },
};
