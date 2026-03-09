// =============================================================================
// Aushadha — Google Authentication Context
// =============================================================================
// Provides dual auth: Google Sign-In + Local JWT authentication.
// Stores user state, tokens, and provides login/logout methods.
// =============================================================================

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import axios from 'axios';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
interface AuthUser {
  email: string;
  name: string;
  picture: string;
  auth_method: 'google' | 'local' | 'skip';
  role: string;
}

interface GoogleAuthContextType {
  user: AuthUser | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  loginWithGoogle: (idToken: string) => Promise<boolean>;
  loginWithLocal: (email: string, password: string) => Promise<{ success: boolean; message: string }>;
  logout: () => void;
  getAuthHeaders: () => Record<string, string>;
}

const GoogleAuthContext = createContext<GoogleAuthContextType>({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true,
  loginWithGoogle: async () => false,
  loginWithLocal: async () => ({ success: false, message: '' }),
  logout: () => {},
  getAuthHeaders: () => ({}),
});

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------
export const useGoogleAuth = () => useContext(GoogleAuthContext);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------
interface GoogleAuthProviderProps {
  children: ReactNode;
  backendUrl?: string;
}

export const GoogleAuthProvider: React.FC<GoogleAuthProviderProps> = ({ children, backendUrl }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const apiBase = backendUrl || import.meta.env.VITE_BACKEND_API_URL || 'http://localhost:8000';

  // Helpers
  const isTokenExpired = (jwtToken: string): boolean => {
    try {
      const payload = JSON.parse(atob(jwtToken.split('.')[1]));
      // exp is in seconds, Date.now() is in ms
      return payload.exp ? payload.exp * 1000 < Date.now() : false;
    } catch {
      return true; // treat malformed token as expired
    }
  };

  // Restore session from localStorage on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('aushadha_auth_token');
    const savedUser = localStorage.getItem('aushadha_auth_user');

    if (savedToken && savedUser) {
      try {
        if (isTokenExpired(savedToken)) {
          // Token expired — clear stale session so user sees login
          localStorage.removeItem('aushadha_auth_token');
          localStorage.removeItem('aushadha_auth_user');
        } else {
          const parsedUser = JSON.parse(savedUser) as AuthUser;
          setToken(savedToken);
          setUser(parsedUser);
        }
      } catch {
        // Corrupted storage — clear it
        localStorage.removeItem('aushadha_auth_token');
        localStorage.removeItem('aushadha_auth_user');
      }
    }
    setIsLoading(false);
  }, []);

  // Global axios 401 interceptor — auto-logout on expired/invalid token
  useEffect(() => {
    const interceptorId = axios.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error?.response?.status === 401) {
          // Clear stale session and redirect to login
          localStorage.removeItem('aushadha_auth_token');
          localStorage.removeItem('aushadha_auth_user');
          setUser(null);
          setToken(null);
          if (!window.location.pathname.startsWith('/login')) {
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
    return () => axios.interceptors.response.eject(interceptorId);
  }, []);


  // Save session to localStorage whenever it changes
  useEffect(() => {
    if (token && user) {
      localStorage.setItem('aushadha_auth_token', token);
      localStorage.setItem('aushadha_auth_user', JSON.stringify(user));
    }
  }, [token, user]);

  // Google Sign-In
  const loginWithGoogle = useCallback(
    async (idToken: string): Promise<boolean> => {
      try {
        const res = await fetch(`${apiBase}/auth/google_verify`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id_token: idToken }),
        });
        const data = await res.json();

        if (data.status === 'Success' && data.data) {
          const authUser: AuthUser = {
            email: data.data.email,
            name: data.data.name,
            picture: data.data.picture || '',
            auth_method: 'google',
            role: data.data.role || '',
          };
          setUser(authUser);
          setToken(data.data.token);
          return true;
        }
        return false;
      } catch (err) {
        console.error('Google login failed:', err);
        return false;
      }
    },
    [apiBase]
  );

  // Local Login (RS256 JWT)
  const loginWithLocal = useCallback(
    async (email: string, password: string): Promise<{ success: boolean; message: string }> => {
      try {
        const res = await fetch(`${apiBase}/auth/local_login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });
        const data = await res.json();

        if (data.status === 'Success' && data.data) {
          const authUser: AuthUser = {
            email: data.data.email,
            name: data.data.name || email.split('@')[0],
            picture: '',
            auth_method: 'local',
            role: data.data.role || '',
          };
          setUser(authUser);
          setToken(data.data.token);
          return { success: true, message: data.message || 'Login successful' };
        }
        return { success: false, message: data.message || 'Login failed' };
      } catch (err) {
        console.error('Local login failed:', err);
        return { success: false, message: 'Network error' };
      }
    },
    [apiBase]
  );

  // Logout
  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem('aushadha_auth_token');
    localStorage.removeItem('aushadha_auth_user');
  }, []);

  // Auth headers for API calls
  const getAuthHeaders = useCallback((): Record<string, string> => {
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
    return {};
  }, [token]);

  return (
    <GoogleAuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: Boolean(user),
        isLoading,
        loginWithGoogle,
        loginWithLocal,
        logout,
        getAuthHeaders,
      }}
    >
      {children}
    </GoogleAuthContext.Provider>
  );
};

export default GoogleAuthProvider;
