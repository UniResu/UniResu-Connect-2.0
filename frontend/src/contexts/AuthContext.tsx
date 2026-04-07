"use client";

/**
 * AuthContext — Provider global de autenticação.
 *
 * Gerencia o estado do usuário logado, tokens JWT,
 * e funções de login/logout (email+senha e ORCID).
 */

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  ReactNode,
} from "react";
import { api } from "@/lib/api";
import { TOKEN_KEY } from "@/lib/constants";
import type { User, LoginResponse } from "@/types/user";

interface AuthContextType {
  user: User | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (email: string, senha: string) => Promise<void>;
  loginWithOrcid: () => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  /** Carrega sessão do localStorage ao montar */
  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken) {
      setToken(savedToken);
      fetchUser(savedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  /** Busca dados do usuário usando o token */
  async function fetchUser(accessToken: string) {
    try {
      const userData = await api.get<User>("/api/auth/me", {
        token: accessToken,
      });
      setUser(userData);
    } catch {
      // Token inválido/expirado
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }

  /** Login com email + senha */
  const login = useCallback(async (email: string, senha: string) => {
    const response = await api.post<LoginResponse>("/api/auth/login", {
      email,
      senha,
    });

    localStorage.setItem(TOKEN_KEY, response.access_token);
    setToken(response.access_token);
    setUser(response.usuario);
  }, []);

  /** Inicia fluxo OAuth ORCID */
  const loginWithOrcid = useCallback(async () => {
    const response = await api.get<{ authorize_url: string }>(
      "/api/auth/orcid/authorize"
    );
    window.location.href = response.authorize_url;
  }, []);

  /** Logout */
  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  /** Re-busca dados do usuário (após edição de perfil) */
  const refreshUser = useCallback(async () => {
    if (token) {
      await fetchUser(token);
    }
  }, [token]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!user,
        login,
        loginWithOrcid,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

/** Hook para acessar o contexto de autenticação */
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth deve ser usado dentro de <AuthProvider>");
  }
  return ctx;
}
