import { createContext, useContext, useMemo, useState, useCallback } from 'react';
import { useAuth } from '../hooks/useAuth';
import type { User } from '../types/db';
import type { ReactNode } from 'react';
import { AuthModal } from '../components/ui/AuthModal';

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
  openAuthModal: (message?: string) => void;
  closeAuthModal: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

/**
 * Voche Auth Provider
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const auth = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalMessage, setAuthModalMessage] = useState<string | undefined>(undefined);

  const openAuthModal = useCallback((message?: string) => {
    setAuthModalMessage(message);
    setIsAuthModalOpen(true);
  }, []);

  const closeAuthModal = useCallback(() => {
    setIsAuthModalOpen(false);
  }, []);

  const value = useMemo(() => ({
    user: auth.user,
    isAuthenticated: auth.isAuthenticated,
    isLoading: auth.isLoading,
    login: auth.login,
    register: auth.register,
    logout: auth.logout,
    authStatus: (auth.authStatus as any),
    openAuthModal,
    closeAuthModal,
  }), [auth.user, auth.isAuthenticated, auth.isLoading, auth.login, auth.register, auth.logout, auth.authStatus, openAuthModal, closeAuthModal]);

  return (
    <AuthContext.Provider value={value}>
      {children}
      <AuthModal isOpen={isAuthModalOpen} onClose={closeAuthModal} message={authModalMessage} />
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