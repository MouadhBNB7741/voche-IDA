import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000';

const axiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor
axiosInstance.interceptors.request.use(
  (config) => {
    const stored = localStorage.getItem('voce_auth_user');

    if (stored) {
      try {
        const user = JSON.parse(stored);
        if (user?.token) {
          config.headers.Authorization = `Bearer ${user.token}`;
        }
      } catch (error) {
        console.error('Failed to parse auth user from localStorage:', error);
      }
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const status = error.response?.status;

    if (status === 401) {
      // Token is expired or invalid — clear storage and redirect to login
      console.warn('Unauthorized. Clearing session and redirecting to login.');
      localStorage.removeItem('voce_auth_user');
      window.location.href = '/login';
    }

    if (status === 403) {
      console.warn('Forbidden. You do not have permission to access this resource.');
    }

    if (status >= 500) {
      console.error('Server error. Please try again later.');
    }

    return Promise.reject(error);
  }
);

export default axiosInstance;