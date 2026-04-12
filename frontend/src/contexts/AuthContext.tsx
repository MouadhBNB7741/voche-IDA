<<<<<<< HEAD
import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

import { authService } from '../services/authService';
import type { AuthUser } from '../services/authService';

interface AuthContextType {
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string, role: AuthUser['role']) => Promise<void>;
  logout: () => void;
=======
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
>>>>>>> origin/main
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

<<<<<<< HEAD
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const currentUser = authService.getCurrentUser();
    setUser(currentUser);
    setIsLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const loggedInUser = await authService.login(email, password);
    setUser(loggedInUser);
  };

  const register = async (email: string, password: string, name: string, role: AuthUser['role']) => {
    const registeredUser = await authService.register(email, password, name, role);
    setUser(registeredUser);
  };

  const logout = () => {
    authService.logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        register,
        logout,
      }}
    >
=======
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
>>>>>>> origin/main
      {children}
    </AuthContext.Provider>
  );
}

<<<<<<< HEAD
export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
=======
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
>>>>>>> origin/main
