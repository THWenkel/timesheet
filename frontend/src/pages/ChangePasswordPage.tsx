import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router";
import { useAuth } from "@/auth/AuthContext";

const MIN_LENGTH = 10;

/**
 * Change the own password. Also the landing page after an administrator reset
 * a password: the user has to choose a new one before anything else works.
 */
export function ChangePasswordPage(): React.JSX.Element {
  const { user, status, changePassword, logout } = useAuth();
  const navigate = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (status === "loading") return <p className="auth-page__loading">Loading…</p>;
  if (user === null) return <Navigate to="/login" replace />;

  const mismatch = repeat !== "" && next !== repeat;
  const tooShort = next !== "" && next.length < MIN_LENGTH;
  const canSubmit = current !== "" && next !== "" && !mismatch && !tooShort && !isSubmitting;

  const handleSubmit = async (event: React.SyntheticEvent<HTMLFormElement>): Promise<void> => {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    const message = await changePassword(current, next);
    setIsSubmitting(false);
    if (message !== null) {
      setError(message);
      return;
    }
    void navigate("/", { replace: true });
  };

  return (
    <main className="auth-page">
      <h1>Timesheet</h1>
      <form className="auth-page__form" onSubmit={(e) => void handleSubmit(e)}>
        <h2>{user.must_change_password ? "Choose a new password" : "Change password"}</h2>
        {user.must_change_password && (
          <p className="auth-page__hint">
            Your password was reset by an administrator. Please choose your own password.
          </p>
        )}
        <label htmlFor="current-password">Current password</label>
        <input
          id="current-password"
          type="password"
          autoComplete="current-password"
          required
          value={current}
          onChange={(e) => {
            setCurrent(e.target.value);
          }}
        />
        <label htmlFor="new-password">New password (at least {MIN_LENGTH} characters)</label>
        <input
          id="new-password"
          type="password"
          autoComplete="new-password"
          required
          value={next}
          onChange={(e) => {
            setNext(e.target.value);
          }}
        />
        <label htmlFor="repeat-password">Repeat new password</label>
        <input
          id="repeat-password"
          type="password"
          autoComplete="new-password"
          required
          value={repeat}
          onChange={(e) => {
            setRepeat(e.target.value);
          }}
        />
        {tooShort && (
          <p className="error-message" role="alert">
            The password must be at least {MIN_LENGTH} characters long.
          </p>
        )}
        {mismatch && (
          <p className="error-message" role="alert">
            The passwords do not match.
          </p>
        )}
        {error !== null && (
          <p className="error-message" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="home-page__save-btn" disabled={!canSubmit}>
          {isSubmitting ? "Saving…" : "Change password"}
        </button>
        {user.must_change_password ? (
          <button
            type="button"
            className="home-page__cancel-btn"
            onClick={() => void logout().then(() => navigate("/login", { replace: true }))}
          >
            Log out
          </button>
        ) : (
          <Link to="/">Back to timesheet</Link>
        )}
      </form>
    </main>
  );
}
