/* =============================================================================
   frontend/src/auth/AuthContext.tsx

   Holds the logged-in user. The session itself is an HttpOnly cookie managed by
   the backend; this context only knows who is logged in (from GET /api/auth/me).
   ============================================================================= */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiClient, onUnauthorized } from "@/api/client";
import type { components } from "@/api/generated";

export type CurrentUser = components["schemas"]["CurrentUser"];

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: CurrentUser | null;
  status: AuthStatus;
  /** Resolves to an error message, or null on success. */
  login: (username: string, password: string) => Promise<string | null>;
  logout: () => Promise<void>;
  /** Resolves to an error message, or null on success. */
  changePassword: (currentPassword: string, newPassword: string) => Promise<string | null>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function detailOf(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null && "detail" in error) {
    const detail = (error as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export function AuthProvider({ children }: { children: React.ReactNode }): React.JSX.Element {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const { data } = await apiClient.GET("/api/auth/me", {});
        if (cancelled) return;
        setUser(data ?? null);
        setStatus(data === undefined ? "anonymous" : "authenticated");
      } catch {
        if (!cancelled) setStatus("anonymous");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // The session expired or was revoked while the app was open.
  useEffect(() => {
    onUnauthorized(() => {
      setUser(null);
      setStatus("anonymous");
    });
    return () => {
      onUnauthorized(null);
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    try {
      const { data, error } = await apiClient.POST("/api/auth/login", {
        body: { username, password },
      });
      if (data === undefined) return detailOf(error, "Login failed.");
      setUser(data);
      setStatus("authenticated");
      return null;
    } catch {
      return "The server cannot be reached.";
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.POST("/api/auth/logout", {});
    } finally {
      setUser(null);
      setStatus("anonymous");
    }
  }, []);

  const changePassword = useCallback(async (currentPassword: string, newPassword: string) => {
    try {
      const { data, error } = await apiClient.POST("/api/auth/change-password", {
        body: { current_password: currentPassword, new_password: newPassword },
      });
      if (data === undefined) return detailOf(error, "Password could not be changed.");
      setUser(data);
      return null;
    } catch {
      return "The server cannot be reached.";
    }
  }, []);

  const value = useMemo(
    () => ({ user, status, login, logout, changePassword }),
    [user, status, login, logout, changePassword],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === null) throw new Error("useAuth must be used inside <AuthProvider>");
  return context;
}
