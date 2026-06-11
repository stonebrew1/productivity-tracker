import { CheckCircle2, Flame, KeyRound, Mail, Trophy, Users, Zap } from "lucide-react";
import { FormEvent, useState } from "react";

type Props = {
  onSubmit: (email: string, password: string, isRegister: boolean) => Promise<void>;
  error: string | null;
  setError: (error: string | null) => void;
};

export function AuthPage({ onSubmit, error, setError }: Props) {
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [isRegister, setIsRegister] = useState(false);
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
      <section className="auth-story">
        <div className="brand auth-brand"><span className="brand-mark"><Zap size={20} fill="currentColor" /></span><strong>Momentum</strong></div>
        <div className="auth-pitch">
          <h1>Turn your goals into <span>daily momentum.</span></h1>
          <p>Plan meaningful work, build streaks, and grow alongside people who keep showing up.</p>
          <div className="auth-features">
            <span><CheckCircle2 /> Focused daily planning</span>
            <span><Flame /> Streaks that reward consistency</span>
            <span><Trophy /> Quests, levels, and badges</span>
            <span><Users /> A social feed built around progress</span>
          </div>
        </div>
        <p className="auth-proof">A workspace for people turning intention into practice.</p>
      </section>
      <section className="auth-panel">
        <div className="auth-mobile-brand"><span className="brand-mark"><Zap size={19} fill="currentColor" /></span><strong>Momentum</strong></div>
        <header><h2>{isRegister ? "Create your account" : "Welcome back"}</h2><p>{isRegister ? "Start building momentum today." : "Continue where you left off."}</p></header>
        <form onSubmit={handleSubmit}>
          <label>Email<span className="auth-input"><Mail size={17} /><input value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></span></label>
          <label>Password<span className="auth-input"><KeyRound size={17} /><input value={password} onChange={(event) => setPassword(event.target.value)} type="password" required /></span></label>
          {error && <div className="alert">{error}</div>}
          <button disabled={busy}>{busy ? "Working..." : isRegister ? "Create account" : "Sign in"}</button>
        </form>
        <p className="auth-switch">{isRegister ? "Already have an account?" : "New to Momentum?"}<button className="text-button" onClick={() => setIsRegister((value) => !value)}>{isRegister ? "Sign in" : "Create account"}</button></p>
      </section>
    </main>
  );
}
