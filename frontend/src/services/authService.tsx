// Mock Authentication Service
export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: 'patient' | 'hcp';
  avatar?: string;
  location?: string;
}

const AUTH_STORAGE_KEY = 'voce_auth_user';

export const authService = {
  getCurrentUser(): AuthUser | null {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  },

  login(email: string, password: string): Promise<AuthUser> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (email && password.length >= 6) {
          const user: AuthUser = {
            id: crypto.randomUUID(),
            name: email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            email,
            role: 'patient',
            location: 'New York, USA', // Default location for demo
            avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${email}`
          };
          localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
          resolve(user);
        } else {
          reject(new Error('Invalid credentials'));
        }
      }, 500);
    });
  },

  register(email: string, password: string, name: string, role: 'patient' | 'hcp'): Promise<AuthUser> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (email && password.length >= 6) {
          const user: AuthUser = {
            id: crypto.randomUUID(),
            name: name || email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
            email,
            role,
            location: 'Not specified',
            avatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${email}`
          };
          localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
          resolve(user);
        } else {
          reject(new Error('Invalid registration data'));
        }
      }, 500);
    });
  },

  logout(): void {
    localStorage.removeItem(AUTH_STORAGE_KEY);
  },

  isAuthenticated(): boolean {
    return !!this.getCurrentUser();
  },
};