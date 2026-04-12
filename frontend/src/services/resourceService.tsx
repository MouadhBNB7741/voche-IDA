<<<<<<< HEAD
// Mock Resource Service
import { mockResources } from '../data/mockData';
import type { Resource } from '../data/mockData';

export interface ExtendedResource extends Resource {
  featured?: boolean;
  requiresAuth?: boolean;
  tags?: string[];
  author?: string;
  publishedDate?: string;
}

// Extended mock resources with additional fields
export const extendedResources: ExtendedResource[] = mockResources.map((resource, index) => ({
  ...resource,
  featured: index < 2, // First 2 are featured
  requiresAuth: index < 2, // Featured resources require auth
  tags: ['healthcare', 'education', resource.category.toLowerCase().replace(' ', '-')],
  author: 'VOCE Editorial Team',
  publishedDate: '2024-12-01',
}));

export const resourceService = {
  getAll(): ExtendedResource[] {
    return extendedResources;
  },

  getById(id: string): ExtendedResource | undefined {
    return extendedResources.find(resource => resource.id === id);
  },

  getFeatured(): ExtendedResource[] {
    return extendedResources.filter(resource => resource.featured);
  },

  search(query: string, filters?: { type?: string; category?: string }): ExtendedResource[] {
    return extendedResources.filter(resource => {
=======
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
>>>>>>> origin/main
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
<<<<<<< HEAD
    if (!resource.requiresAuth) return true;
    return isAuthenticated;
  },
};
=======
    if (!resource.requires_auth) return true;
    return isAuthenticated;
  },
};
>>>>>>> origin/main
