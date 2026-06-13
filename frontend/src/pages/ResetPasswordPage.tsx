import { Check, KeyRound, Link2Off, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api, clearTokens } from "../api/client";
import { AuthRecoveryLayout } from "./ForgotPasswordPage";

const passwordChecks = [
  ["10+ characters", (value: string) => value.length >= 10],
  ["Lowercase", (value: string) => /[a-z]/.test(value)],
  ["Uppercase", (value: string) => /[A-Z]/.test(value)],
  ["Number", (value: string) => /\d/.test(value)]
] as const;

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const passwordStrong = passwordChecks.every(([, check]) => check(password));

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    if (!passwordStrong) {
      setError("Password does not meet all requirements.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    setBusy(true);
    try {
      const result = await api.resetPassword(token, password);
      clearTokens();
      setMessage(result.message);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Unable to reset password.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthRecoveryLayout>
      {!token ? (
        <div className="recovery-complete error">
          <span><Link2Off size={26} /></span>
          <h1>Incomplete reset link</h1>
          <p>Request a fresh password reset email to continue.</p>
          <Link className="recovery-primary-link" to="/forgot-password">Request another link</Link>
        </div>
      ) : message ? (
        <div className="recovery-complete">
          <span><ShieldCheck size={26} /></span>
          <h1>Password changed</h1>
          <p>{message}</p>
          <a className="recovery-primary-link" href="/login">Sign in</a>
        </div>
      ) : (
        <>
          <header><h1>Choose a new password</h1><p>This will sign your account out on every other device.</p></header>
          <form className="recovery-form" onSubmit={submit}>
            <label>New password<span className="auth-input"><KeyRound size={17} /><input autoComplete="new-password" autoFocus required type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></span></label>
            <div className="password-check-list recovery-password-checks">
              {passwordChecks.map(([label, check]) => <span className={check(password) ? "met" : ""} key={label}><Check size={12} />{label}</span>)}
            </div>
            <label>Confirm password<span className="auth-input"><KeyRound size={17} /><input autoComplete="new-password" required type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></span></label>
            {error && <div className="alert">{error}</div>}
            <button disabled={busy || !passwordStrong || password !== confirmPassword}>{busy ? "Resetting..." : "Reset password"}</button>
          </form>
        </>
      )}
    </AuthRecoveryLayout>
  );
}
