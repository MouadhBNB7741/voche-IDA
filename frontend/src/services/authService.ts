import { apiClient } from "../lib/apiClient";
import { AUTH, USERS } from "../lib/api";
import Cookies from "universal-cookie";
import type {
  User,
  LoginRequest,
  LoginResponse,
  RegisterRequest,
} from "../types/db";

const cookies = new Cookies();

/**
 * Handle platform secure session storage for JWT using universal-cookie.
 * Ensures cross-platform compatibility and standardized pathing.
 */
const platformSession = {
  setToken: (token: string) => {
    try {
      // 24 hour secure, strict cookie
      cookies.set("voche_token", token, {
        path: "/",
        maxAge: 86400,
        secure: true,
        sameSite: "strict",
      });
    } catch (err) {
      console.error("[AUTH SESSION ERROR - SET]", err);
    }
  },
  clearToken: () => {
    try {
      cookies.remove("voche_token", { path: "/" });
    } catch (err) {
      console.error("[AUTH SESSION ERROR - REMOVE]", err);
    }
  },
};

/**
 * Voche Unified Auth Service
 * Integrated with universal-cookie and hardened apiClient.
 */
export const authService = {
  /**
   * Register a new user on VOCHE
   */
  register: async (data: RegisterRequest): Promise<LoginResponse> => {
    try {
      const response = await apiClient.post<LoginResponse>(AUTH.REGISTER, data);
      if (response.data.access_token) {
        platformSession.setToken(response.data.access_token);
      }
      return response.data;
    } catch (err) {
      // apiClient already handles error normalization via interceptor
      throw err;
    }
  },

  /**
   * Standard Email/Password login
   */
  login: async (data: LoginRequest): Promise<LoginResponse> => {
    try {
      const response = await apiClient.post<LoginResponse>(AUTH.LOGIN, data);
      if (response.data.access_token) {
        platformSession.setToken(response.data.access_token);
      }
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Sign in with the ID token from the "Sign in with Google" button.
   */
  loginWithGoogle: async (credential: string): Promise<LoginResponse> => {
    const response = await apiClient.post<LoginResponse>(AUTH.GOOGLE, { credential });
    if (response.data.access_token) {
      platformSession.setToken(response.data.access_token);
    }
    return response.data;
  },

  /**
   * Fetch full user profile details based on current session token.
   */
  getMe: async (): Promise<User> => {
    try {
      const response = await apiClient.get<User>(USERS.ME);
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Clear the cookie straight away, and revoke the token on the server in the background.
   */
  logout: async (): Promise<void> => {
    const token = cookies.get("voche_token");
    platformSession.clearToken();
    if (token) {
      apiClient
        .post(AUTH.LOGOUT, null, { headers: { Authorization: `Bearer ${token}` } })
        .catch((err) => {
          // Signed out on this device anyway; the token still expires on its own
          console.warn("[AUTH] Could not revoke the token on the server", err);
        });
    }
  },

  /**
   * Forgot password using email link.
   */
  forgotPassword: async (email: string): Promise<void> => {
    try {
      await apiClient.post(AUTH.FORGOT_PASSWORD, { email });
    } catch (err) {
      throw err;
    }
  },

  /**
   * Reset password using token from email link.
   */
  resetPassword: async (token: string, new_password: string): Promise<void> => {
    try {
      await apiClient.post(AUTH.RESET_PASSWORD, { token, new_password });
    } catch (err) {
      throw err;
    }
  },
  
};

export default authService;
