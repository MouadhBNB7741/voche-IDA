import axios, { AxiosError, type InternalAxiosRequestConfig, type AxiosResponse } from 'axios';
import Cookies from 'universal-cookie';

const cookies = new Cookies();
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Voche Hardened API Client
 * Responsibilities: HTTP transport, cookie-based token injection, error normalization.
 */
export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  },
});

/**
 * Request Interceptor: Attach Bearer Token from Cookies
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    try {
      const token = cookies.get('voche_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    } catch (err) {
      console.error('[API CLIENT ERROR - REQUEST INTERCEPTOR]', err);
      return config; // Fallback to original config to avoid blocking
    }
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  }
);

/**
 * Response Interceptor: Normalize errors and handle session security
 */
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    if (response.status >= 200 && response.status < 300) {
      return response;
    }
    return Promise.reject(new Error(`Unexpected status code: ${response.status}`));
  },
  (error: AxiosError) => {
    try {
      const data = error.response?.data as any;
      // Some errors send details as an object, e.g. { code: 'account_suspended', message, suspended_until }
      const detail = data?.detail && typeof data.detail === 'object' && !Array.isArray(data.detail) ? data.detail : null;

      // 1. Session Invalidation (HTTP 401, or 403 for a suspended account)
      if (error.response?.status === 401 || detail?.code === 'account_suspended') {
        if (cookies.get('voche_token')) {
          console.warn('Session ended. Purging auth cookie.');
          cookies.remove('voche_token', { path: '/' });
        }
      }

      // 2. Error Normalization
      // Guard against non-standard error structures
      const normalizedError = {
        status: error.response?.status || 500,
        message: detail?.message || detail?.error?.message || data?.detail || data?.message || error.message || 'An unexpected error occurred',
        code: detail?.code,
        details: detail,
        originalError: error,
      };
      
      return Promise.reject(normalizedError);
    } catch (err) {
      // Ultimate fallback to prevent client crash
      return Promise.reject({
        status: 500,
        message: 'System critical failure in API transport layer',
        originalError: err
      });
    }
  }
);

export default apiClient;
