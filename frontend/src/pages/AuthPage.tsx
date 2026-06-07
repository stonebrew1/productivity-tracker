import { FormEvent, useState } from "react";

type Props = {
  onSubmit: (email: string, password: string, isRegister: boolean) => Promise<void>;
  error: string | null;
  setError: (error: string | null) => void;
};

export function AuthPage({ onSubmit, error, setError }: Props) {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [isRegister, setIsRegister] = useState(true);
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await onSubmit(email, password, isRegister);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-screen">
      <section className="auth-panel">
        <h1>Productivity Tracker</h1>
        <form onSubmit={handleSubmit}>
          <label>
            Email
            <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required />
          </label>
          <label>
            Password
            <input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required />
          </label>
          {error && <div className="alert">{error}</div>}
          <button disabled={busy}>{busy ? "Working..." : isRegister ? "Create account" : "Login"}</button>
        </form>
        <button className="text-button" onClick={() => setIsRegister((value) => !value)}>
          {isRegister ? "I already have an account" : "Create a new account"}
        </button>
      </section>
    </main>
  );
}
