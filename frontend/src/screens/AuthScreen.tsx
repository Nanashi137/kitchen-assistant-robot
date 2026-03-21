import { useState } from "react";

type Mode = "login" | "signup";

interface AuthFormState {
  username: string;
  password: string;
  email: string;
}

interface AuthScreenProps {
  apiBaseUrl: string;
  onAuthSuccess: (token: string, tokenType: string) => void;
}

export function AuthScreen({ apiBaseUrl, onAuthSuccess }: AuthScreenProps) {
  const [mode, setMode] = useState<Mode>("login");
  const [form, setForm] = useState<AuthFormState>({
    username: "",
    password: "",
    email: "",
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const handleChange = (field: keyof AuthFormState, value: string) => {
    setForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const handleSubmit = async (event: any) => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (!form.username.trim() || !form.password.trim()) {
      setError("Username and password are required.");
      return;
    }

    if (mode === "signup" && form.password.length < 6) {
      setError("Password must be at least 6 characters long.");
      return;
    }

    setIsSubmitting(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/signup";
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: form.username.trim(),
          password: form.password,
          email:
            mode === "signup" && form.email.trim()
              ? form.email.trim()
              : undefined,
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          (data && (data.detail || data.message)) ||
          (mode === "login"
            ? "Unable to log in with those credentials."
            : "Unable to create your account.");
        throw new Error(
          typeof detail === "string"
            ? detail
            : "Something went wrong. Please try again.",
        );
      }

      if (!data?.access_token) {
        throw new Error("API did not return an access token.");
      }

      const token = data.access_token as string;
      const tokenType = (data.token_type as string) || "bearer";

      try {
        localStorage.setItem("auth_token", token);
        localStorage.setItem("auth_token_type", tokenType);
      } catch {
        // ignore storage errors
      }

      onAuthSuccess(token, tokenType);
      setSuccess(
        mode === "login"
          ? "Logged in successfully. Your token is saved locally and ready to use."
          : "Account created and logged in. Your token is saved locally and ready to use.",
      );
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Something went wrong. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleModeToggle = () => {
    setMode((prev) => (prev === "login" ? "signup" : "login"));
    setError(null);
    setSuccess(null);
  };

  return (
    <div className="app-shell">
      <div className="app-panel">
        <header className="app-header">
          <h1 className="app-title">Kitchen Assistant</h1>
          <p className="app-subtitle">
            {mode === "login"
              ? "Welcome back. Log in to continue."
              : "Create an account to get started."}
          </p>
        </header>

        <div className="card">
          <div className="card-toggle">
            <button
              type="button"
              className={
                mode === "login" ? "toggle-button active" : "toggle-button"
              }
              onClick={() => setMode("login")}
              disabled={isSubmitting}
            >
              Log in
            </button>
            <button
              type="button"
              className={
                mode === "signup" ? "toggle-button active" : "toggle-button"
              }
              onClick={() => setMode("signup")}
              disabled={isSubmitting}
            >
              Sign up
            </button>
          </div>

          <form className="card-form" onSubmit={handleSubmit} noValidate>
            <label className="field">
              <span className="field-label">Username</span>
              <input
                type="text"
                autoComplete={mode === "login" ? "username" : "new-username"}
                value={form.username}
                onChange={(event) =>
                  handleChange("username", event.target.value)
                }
                placeholder="Choose a username"
                required
              />
            </label>

            {mode === "signup" && (
              <label className="field">
                <span className="field-label">Email (optional)</span>
                <input
                  type="email"
                  autoComplete="email"
                  value={form.email}
                  onChange={(event) =>
                    handleChange("email", event.target.value)
                  }
                  placeholder="you@example.com"
                />
              </label>
            )}

            <label className="field">
              <span className="field-label">Password</span>
              <input
                type="password"
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
                value={form.password}
                onChange={(event) =>
                  handleChange("password", event.target.value)
                }
                placeholder={
                  mode === "login"
                    ? "Your password"
                    : "Create a strong password"
                }
                required
                minLength={6}
              />
            </label>

            {error && <p className="feedback feedback-error">{error}</p>}
            {success && !error && (
              <p className="feedback feedback-success">{success}</p>
            )}

            <button
              className="primary-button"
              type="submit"
              disabled={isSubmitting}
            >
              {isSubmitting
                ? mode === "login"
                  ? "Logging in..."
                  : "Creating account..."
                : mode === "login"
                  ? "Log in"
                  : "Create account"}
            </button>
          </form>

          <button
            type="button"
            className="ghost-link"
            onClick={handleModeToggle}
            disabled={isSubmitting}
          >
            {mode === "login"
              ? "Don't have an account? Sign up"
              : "Already have an account? Log in"}
          </button>
        </div>
      </div>
    </div>
  );
}
