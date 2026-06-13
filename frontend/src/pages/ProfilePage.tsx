import { Check, KeyRound, ShieldCheck, Trash2, Upload, UserRound, X } from "lucide-react";
import { ChangeEvent, FormEvent, useRef, useState } from "react";

import { api } from "../api/client";
import { UserAvatar } from "../components/UserAvatar";
import type { Stats, User } from "../types/domain";

type Props = {
  user: User;
  stats: Stats | null;
  onUserChange: (user: User) => void;
  onDeleted: () => void;
  onError: (message: string | null) => void;
};

const passwordChecks = [
  ["10+ characters", (value: string) => value.length >= 10],
  ["Lowercase", (value: string) => /[a-z]/.test(value)],
  ["Uppercase", (value: string) => /[A-Z]/.test(value)],
  ["Number", (value: string) => /\d/.test(value)]
] as const;

export function ProfilePage({ user, stats, onUserChange, onDeleted, onError }: Props) {
  const [name, setName] = useState(user.display_name ?? "");
  const [bio, setBio] = useState(user.bio ?? "");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const displayName = user.display_name || user.email.split("@")[0];
  const passwordStrong = passwordChecks.every(([, check]) => check(newPassword));

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setMessage(null);
    onError(null);
    try {
      await action();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update account");
    } finally {
      setBusy(false);
    }
  }

  function submitProfile(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      const updated = await api.updateMe({ display_name: name, bio });
      onUserChange(updated);
      setMessage("Profile saved.");
    });
  }

  function uploadAvatar(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    void run(async () => {
      const updated = await api.uploadAvatar(file);
      onUserChange(updated);
      setMessage("Avatar updated.");
    });
  }

  function submitPassword(event: FormEvent) {
    event.preventDefault();
    if (newPassword !== confirmPassword) {
      onError("New passwords do not match.");
      return;
    }
    if (!passwordStrong) {
      onError("New password does not meet all requirements.");
      return;
    }
    void run(async () => {
      await api.changePassword(currentPassword, newPassword);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setMessage("Password changed.");
    });
  }

  function deleteAccount(event: FormEvent) {
    event.preventDefault();
    void run(async () => {
      await api.deleteAccount(deletePassword, deleteConfirmation);
      onDeleted();
    });
  }

  return (
    <section className="profile-page">
      <header className="page-header">
        <div>
          <h1>Profile</h1>
          <p>Manage how you appear to friends and secure your account.</p>
        </div>
      </header>

      {message && <div className="profile-success"><Check size={16} />{message}</div>}

      <section className="profile-hero">
        <UserAvatar name={displayName} avatarUrl={user.avatar_url} className="profile-avatar" />
        <div>
          <strong>{displayName}</strong>
          <span>{user.email}</span>
          <small>Member since {new Date(user.created_at).toLocaleDateString()}</small>
        </div>
        <div className="profile-avatar-actions">
          <input ref={fileInput} hidden accept="image/jpeg,image/png,image/webp" type="file" onChange={uploadAvatar} />
          <button disabled={busy} onClick={() => fileInput.current?.click()}><Upload size={16} />Upload photo</button>
          {user.avatar_url && <button className="text-button" disabled={busy} onClick={() => void run(async () => {
            const updated = await api.removeAvatar();
            onUserChange(updated);
            setMessage("Avatar removed.");
          })}><X size={15} />Remove</button>}
          <small>JPEG, PNG, or WebP. Maximum 2 MB.</small>
        </div>
      </section>

      <div className="profile-grid">
        <form className="profile-settings-panel" onSubmit={submitProfile}>
          <header><UserRound size={18} /><div><h2>Public profile</h2><p>Visible to people across Momentum.</p></div></header>
          <label>Display name<input maxLength={80} minLength={2} required value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>Current goal<textarea maxLength={500} placeholder="What are you working toward?" value={bio} onChange={(event) => setBio(event.target.value)} /></label>
          <footer><span>{bio.length} / 500</span><button disabled={busy}>Save profile</button></footer>
        </form>

        <section className="profile-stats-panel">
          <header><ShieldCheck size={18} /><div><h2>Account overview</h2><p>Your current Momentum progress.</p></div></header>
          <div className="profile-stat-grid">
            <div><strong>{stats?.level ?? 1}</strong><span>Level</span></div>
            <div><strong>{stats?.xp_total ?? 0}</strong><span>Total XP</span></div>
            <div><strong>{stats?.current_streak ?? 0}</strong><span>Day streak</span></div>
            <div><strong>{stats?.completed_tasks ?? 0}</strong><span>Tasks done</span></div>
          </div>
          <p className="verified-email"><Check size={14} />Email verified</p>
        </section>
      </div>

      <form className="profile-settings-panel password-panel" onSubmit={submitPassword}>
        <header><KeyRound size={18} /><div><h2>Change password</h2><p>Changing it does not expose your current password.</p></div></header>
        <div className="profile-password-fields">
          <label>Current password<input autoComplete="current-password" required type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
          <label>New password<input autoComplete="new-password" required type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
          <label>Confirm new password<input autoComplete="new-password" required type="password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
        </div>
        <div className="password-check-list">
          {passwordChecks.map(([label, check]) => <span className={check(newPassword) ? "met" : ""} key={label}><Check size={12} />{label}</span>)}
        </div>
        <footer><span /><button disabled={busy || !currentPassword || !passwordStrong || newPassword !== confirmPassword}>Change password</button></footer>
      </form>

      <form className="danger-zone" onSubmit={deleteAccount}>
        <header><Trash2 size={18} /><div><h2>Delete account</h2><p>Permanently removes your tasks, social activity, groups you lead, and progression.</p></div></header>
        <div className="danger-fields">
          <label>Password<input autoComplete="current-password" required type="password" value={deletePassword} onChange={(event) => setDeletePassword(event.target.value)} /></label>
          <label>Type DELETE<input required value={deleteConfirmation} onChange={(event) => setDeleteConfirmation(event.target.value)} /></label>
        </div>
        <button disabled={busy || !deletePassword || deleteConfirmation !== "DELETE"}><Trash2 size={16} />Delete my account</button>
      </form>
    </section>
  );
}
