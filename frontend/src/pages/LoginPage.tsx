import { useState } from "react";
import { Navigate, useNavigate } from "react-router";
import { useAuth } from "@/auth/AuthContext";

/** Login form. Sends username and password to POST /api/auth/login (over HTTPS in production). */
export function LoginPage(): React.JSX.Element {
  const { user, status, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (status === "authenticated" && user !== null) {
    return <Navigate to={user.must_change_password ? "/change-password" : "/"} replace />;
  }

  const handleSubmit = async (event: React.SyntheticEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    const message = await login(username.trim(), password);
    setIsSubmitting(false);
    if (message !== null) {
      setError(message);
      setPassword("");
      return;
    }
    void navigate("/", { replace: true });
  };

  return (
    <main className="auth-page">
      <h1>Timesheet</h1>
      <form className="auth-page__form" onSubmit={(e) => void handleSubmit(e)}>
        <h2>Sign in</h2>
        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          type="text"
          autoComplete="username"
          autoFocus
          required
          value={username}
          onChange={(e) => {
            setUsername(e.target.value);
          }}
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
          }}
        />
        {error !== null && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <button
          type="submit"
          className="home-page__save-btn"
          disabled={isSubmitting || username.trim() === "" || password === ""}
        >
          {isSubmitting ? "Signing in…" : "Sign in"}
        </button>
        <p className="auth-page__hint">
          Forgot your password? Ask an administrator for a one-time password.
        </p>
      </form>
    </main>
  );
}
