import { Navigate } from "react-router";
import { useAuth } from "@/auth/AuthContext";

/**
 * Route guard: anonymous visitors go to /login, users with a pending password
 * reset go to /change-password. Everyone else sees the children.
 */
export function RequireAuth({ children }: { children: React.ReactNode }): React.JSX.Element {
  const { user, status } = useAuth();

  if (status === "loading") {
    return <p className="auth-page__loading">Loading…</p>;
  }
  if (user === null) {
    return <Navigate to="/login" replace />;
  }
  if (user.must_change_password) {
    return <Navigate to="/change-password" replace />;
  }
  return <>{children}</>;
}
