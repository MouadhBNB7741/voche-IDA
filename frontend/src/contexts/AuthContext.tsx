import { createContext, useContext, useMemo } from 'react';
import { useAuth } from '../hooks/useAuth';
import type { User } from '../types/db';
import type { ReactNode } from 'react';

/**
 * Voche Unified Auth Context Type
 */
interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: any) => Promise<any>;
  register: (data: any) => Promise<any>;
  logout: () => void;
  authStatus: 'error' | 'pending' | 'success' | 'idle'; 
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Voche Auth Provider
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();

  const value = useMemo(() => ({
    user: auth.user,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    login: auth.login,
    register: auth.register,
    logout: auth.logout,
    authStatus: (auth.authStatus as any),
  }), [auth.user, auth.isAuthenticated, auth.isLoading, auth.login, auth.register, auth.logout, auth.authStatus]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// Re-export useAuth from here to satisfy components importing from this path
export { useAuth };

/**
 * Standard access hook for Auth throughout the component tree.
 */
export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
