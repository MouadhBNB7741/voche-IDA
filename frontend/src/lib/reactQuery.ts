import { QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

/**
 * Voche React Query Global Configuration
 * Responsibilities: State caching, data lifecycle, error management.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2, // Max 2 retries on failure
      refetchOnWindowFocus: false, // Prevents unnecessary jumps on refocus
      staleTime: 5 * 60 * 1000, // Keep data fresh for 5 mins
      gcTime: 30 * 60 * 1000, // Keep in memory for 30 mins
      throwOnError: false, // Handle errors in individual components or global via hooks
    },
    mutations: {
      retry: 0, // No automatic retry for mutations
      /**
       * Mutation Global Error Handling (Optional: standardizes toast messaging)
       */
      onError: (error: any) => {
        const message = error.message || 'Action failed - please try again';
        toast.error(message);
        console.error('[MUTATION ERROR]', {
          message,
          error: error.originalError || error,
        });
      },
    },
  },
});

/**
 * Standard Query Global Handler
 * Used for standardized UI feedback based on HTTP failures.
 */
export const handleGlobalError = (error: any) => {
  const message = error.message || 'An unexpected error occurred';
  
  // Show toast notification via Sonner
  toast.error(message);
  
  // Detailed logging for debugging
  console.error('[API ERROR]', {
    status: error.response?.status,
    url: error.config?.url,
    message,
    fullError: error
  });
};

export default queryClient;
