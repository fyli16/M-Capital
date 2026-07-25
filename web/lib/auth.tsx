"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import * as api from "@/lib/api/client";

interface AuthState {
  token: string | null;
  isAuthenticated: boolean;
  ready: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, role?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setTokenState(api.getToken());
    setReady(true);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tok = await api.login(email, password);
    api.setToken(tok);
    setTokenState(tok);
  }, []);

  const register = useCallback(
    async (email: string, password: string, role = "analyst") => {
      await api.register(email, password, role);
      await login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    api.setToken(null);
    setTokenState(null);
  }, []);

  const value = useMemo<AuthState>(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      ready,
      login,
      register,
      logout,
    }),
    [token, ready, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
