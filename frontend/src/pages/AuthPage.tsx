import { Check, CheckCircle2, Flame, KeyRound, Mail, Trophy, UserRound, Users, Zap } from "lucide-react";
import { FormEvent, useState } from "react";

import { api } from "../api/client";
import type { RegistrationResponse } from "../types/domain";

type Props = {
  onLogin: (email: string, password: string) => Promise<void>;
  onRegister: (displayName: string, email: string, password: string) => Promise<RegistrationResponse>;
  onResend: (email: string) => Promise<{ message: string; verification_url: string | null }>;
  error: string | null;
  setError: (error: string | null) => void;
};

const passwordChecks = [
  ["At least 10 characters", (value: string) => value.length >= 10],
  ["Lowercase letter", (value: string) => /[a-z]/.test(value)],
  ["Uppercase letter", (value: string) => /[A-Z]/.test(value)],
  ["Number", (value: string) => /\d/.test(value)]
] as const;

export function AuthPage({ onLogin, onRegister, onResend, error, setError }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("demo@example.com");
  const [password, setPassword] = useState("password123");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isRegister, setIsRegister] = useState(false);
  const [busy, setBusy] = useState(false);
  const [verificationCode, setVerificationCode] = useState("");
  const [verificationMessage, setVerificationMessage] = useState<string | null>(null);
  const [registration, setRegistration] = useState<RegistrationResponse | null>(null);
  const strength = passwordChecks.filter(([, check]) => check(password)).length;
  const developmentVerificationUrl = registration?.verification_url
    ? (() => {
        const url = new URL(registration.verification_url);
        return `${window.location.origin}${url.pathname}${url.search}`;
      })()
    : null;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (isRegister) {
        if (password !== confirmPassword) throw new Error("Passwords do not match.");
        if (strength < passwordChecks.length) throw new Error("Password does not meet all requirements.");
        setRegistration(await onRegister(displayName, email, password));
      } else {
        await onLogin(email, password);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setBusy(true);
    setError(null);
    try {
      const result = await onResend(registration?.email ?? email);
      setRegistration((current) => current ? { ...current, ...result } : current);
      setVerificationMessage("A new link and code were sent.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to resend verification email");
    } finally {
      setBusy(false);
    }
  }

  async function confirmCode(event: FormEvent) {
    event.preventDefault();
    if (!registration || verificationCode.length !== 6) return;
    setBusy(true);
    setError(null);
    setVerificationMessage(null);
    try {
      const result = await api.verifyEmailCode(registration.email, verificationCode);
      setVerificationMessage(result.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to confirm code");
    } finally {
      setBusy(false);
    }
  }

  function switchMode() {
    setIsRegister((value) => !value);
    setRegistration(null);
    setConfirmPassword("");
    setError(null);
    if (!isRegister) {
      setEmail("");
      setPassword("");
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
        {registration ? (
          <div className="verification-prompt">
            <span><Mail size={24} /></span>
            <h2>Check your email</h2>
            <p>We sent a confirmation link to <strong>{registration.email}</strong>. Confirm it before signing in.</p>
            {developmentVerificationUrl && <a href={developmentVerificationUrl}>Open development verification link</a>}
            <div className="verification-divider"><span>or enter the code</span></div>
            <form className="verification-code-form" onSubmit={confirmCode}>
              <input
                aria-label="Six digit confirmation code"
                autoComplete="one-time-code"
                inputMode="numeric"
                maxLength={6}
                pattern="\d{6}"
                placeholder="000000"
                value={verificationCode}
                onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
              />
              <button disabled={busy || verificationCode.length !== 6}>
                <Check size={16} />Confirm code
              </button>
            </form>
            {verificationMessage && <div className="verification-success">{verificationMessage}</div>}
            {error && <div className="alert">{error}</div>}
            <button className="verification-resend" disabled={busy} onClick={() => void resend()}>
              <Mail size={16} />{busy ? "Sending..." : "Resend verification email"}
            </button>
            <button className="text-button" onClick={() => { setRegistration(null); setIsRegister(false); }}>Back to sign in</button>
          </div>
        ) : (
          <>
            <header><h2>{isRegister ? "Create your account" : "Welcome back"}</h2><p>{isRegister ? "Start building momentum today." : "Continue where you left off."}</p></header>
            <form onSubmit={handleSubmit}>
              {isRegister && <label>Name<span className="auth-input"><UserRound size={17} /><input autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} required /></span></label>}
              <label>Email<span className="auth-input"><Mail size={17} /><input autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} type="email" required /></span></label>
              <label>Password<span className="auth-input"><KeyRound size={17} /><input autoComplete={isRegister ? "new-password" : "current-password"} value={password} onChange={(event) => setPassword(event.target.value)} type="password" required /></span></label>
              {isRegister && (
                <>
                  <div className={`password-strength strength-${strength}`}>
                    <div>{passwordChecks.map(([label]) => <i key={label} />)}</div>
                    <span>{strength < 2 ? "Weak" : strength < 4 ? "Getting stronger" : "Strong"}</span>
                  </div>
                  <div className="password-requirements">
                    {passwordChecks.map(([label, check]) => <span className={check(password) ? "met" : ""} key={label}><Check size={12} />{label}</span>)}
                  </div>
                  <label>Confirm password<span className="auth-input"><KeyRound size={17} /><input autoComplete="new-password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} type="password" required /></span></label>
                </>
              )}
              {error && <div className="alert">{error}</div>}
              <button disabled={busy}>{busy ? "Working..." : isRegister ? "Create account" : "Sign in"}</button>
            </form>
            <p className="auth-switch">{isRegister ? "Already have an account?" : "New to Momentum?"}<button className="text-button" onClick={switchMode}>{isRegister ? "Sign in" : "Create account"}</button></p>
          </>
        )}
      </section>
    </main>
  );
}
