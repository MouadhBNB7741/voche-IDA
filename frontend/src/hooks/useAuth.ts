import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import Cookies from 'universal-cookie';
import { authService } from '../services/authService';
import type { User, LoginRequest, RegisterRequest } from '../types/db';

const cookies = new Cookies();

/**
 * Voche Custom Hook for All Authentication State Management
 * Internally uses TanStack React Query and universal-cookie for session logic.
 */
export function useAuth() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  /**
   * Reactive check for auth presence via universal-cookie
   */
  const hasTokenAvailable = () => {
    try {
      return !!cookies.get('voche_token');
    } catch (err) {
      return false;
    }
  };

  /**
   * Fetch current authenticated user profile
   * Cascades the session based on token presence.
   */
  const {
    data: user,
    isLoading: isFetchingUser,
    status: authStatus
  } = useQuery<User>({
    queryKey: ['auth', 'me'],
    queryFn: authService.getMe,
    enabled: hasTokenAvailable(),
    staleTime: 60 * 60 * 1000,
    retry: 1, // Minimal retry for profile sync
  });

  /**
   * Unified Authentication Flow
   */
  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) => authService.login(data),
    onSuccess: async () => {
      // Invalidate and refetch immediately
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      navigate('/patientdashboard');
    },
  });

  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) => authService.register(data),
    onSuccess: async () => {
      // Invalidate and refetch immediately
      await queryClient.invalidateQueries({ queryKey: ['auth', 'me'] });
      navigate('/patientdashboard');
    },
  });

  const logout = async () => {
    await authService.logout();
    queryClient.removeQueries({ queryKey: ['auth'] });
    queryClient.clear();
    navigate('/login');
  };

  const isInitialLoading = isFetchingUser && !user;

  return {
    user: user || null,
    isAuthenticated: !!user,
    isLoading: isInitialLoading || loginMutation.isPending || registerMutation.isPending,
    isFetchingUser,
    login: loginMutation.mutateAsync,
    register: registerMutation.mutateAsync,
    logout,
    loginStatus: loginMutation.status,
    registerStatus: registerMutation.status,
    authStatus,
    loginError: loginMutation.error,
    registerError: registerMutation.error,
    isProcessing: loginMutation.isPending || registerMutation.isPending
  };
}

export default useAuth;
