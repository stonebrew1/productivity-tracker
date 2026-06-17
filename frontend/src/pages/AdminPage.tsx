import { Ban, CheckCircle2, ChevronLeft, ChevronRight, Search, ShieldCheck, Unlock } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { AdminSummary, AdminUserPage } from "../types/domain";

const PAGE_SIZE = 12;

export function AdminPage({ onError }: { onError: (message: string | null) => void }) {
  const [summary, setSummary] = useState<AdminSummary | null>(null);
  const [users, setUsers] = useState<AdminUserPage | null>(null);
  const [query, setQuery] = useState("");
  const [appliedQuery, setAppliedQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(nextQuery = appliedQuery, nextOffset = offset) {
    try {
      const [nextSummary, nextUsers] = await Promise.all([
        api.adminStatistics(),
        api.adminUsers(nextQuery, nextOffset, PAGE_SIZE)
      ]);
      setSummary(nextSummary);
      setUsers(nextUsers);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to load administrator data");
    }
  }

  useEffect(() => {
    void load("", 0);
  }, []);

  function search(event: FormEvent) {
    event.preventDefault();
    const normalized = query.trim();
    setAppliedQuery(normalized);
    setOffset(0);
    void load(normalized, 0);
  }

  async function toggleBlock(userId: string, blocked: boolean) {
    setBusyId(userId);
    onError(null);
    try {
      if (blocked) await api.unblockUser(userId);
      else await api.blockUser(userId);
      await load();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update account");
    } finally {
      setBusyId(null);
    }
  }

  function changePage(nextOffset: number) {
    setOffset(nextOffset);
    void load(appliedQuery, nextOffset);
  }

  return (
    <section className="admin-page">
      <header className="page-header">
        <div><h1>Administration</h1><p>Manage access and monitor the health of the Momentum workspace.</p></div>
        <span className="admin-role"><ShieldCheck size={16} />Administrator</span>
      </header>

      <div className="metrics-grid admin-metrics">
        <Metric label="Users" value={summary?.total_users ?? 0} />
        <Metric label="Verified" value={summary?.verified_users ?? 0} />
        <Metric label="Blocked" value={summary?.blocked_users ?? 0} />
        <Metric label="Tasks" value={summary?.total_tasks ?? 0} />
        <Metric label="Completed" value={summary?.completed_tasks ?? 0} />
        <Metric label="Achievements" value={summary?.total_achievements ?? 0} />
      </div>

      <section className="panel admin-summary">
        <div><span>Platform completion</span><strong>{summary?.completion_rate ?? 0}%</strong></div>
        <div className="xp-track"><i style={{ width: `${summary?.completion_rate ?? 0}%` }} /></div>
        <footer><span>{summary?.total_groups ?? 0} groups</span><span>{summary?.administrators ?? 0} administrators</span></footer>
      </section>

      <section className="panel admin-users">
        <div className="section-heading"><h2>User accounts</h2><span>{users?.total ?? 0} total</span></div>
        <form className="admin-search" onSubmit={search}>
          <label className="search-field"><Search size={17} /><input placeholder="Search name or email" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
          <button>Search</button>
        </form>
        <div className="admin-user-list">
          {users?.items.map((user) => (
            <article className="admin-user-row" key={user.id}>
              <div className="admin-user-identity">
                <span>{(user.display_name || user.email)[0].toUpperCase()}</span>
                <div><strong>{user.display_name || user.email.split("@")[0]}</strong><small>{user.email}</small></div>
              </div>
              <div className="admin-user-facts">
                <span>{user.completed_tasks}/{user.total_tasks} tasks</span>
                <span>{user.is_email_verified ? <CheckCircle2 size={13} /> : null}{user.is_email_verified ? "Verified" : "Unverified"}</span>
                <span className={user.is_blocked ? "blocked" : ""}>{user.is_blocked ? "Blocked" : user.role}</span>
              </div>
              <button
                className={user.is_blocked ? "secondary-button" : "danger-button"}
                disabled={busyId === user.id || user.role === "admin"}
                title={user.is_blocked ? "Unblock account" : "Block account"}
                onClick={() => void toggleBlock(user.id, user.is_blocked)}
              >
                {user.is_blocked ? <Unlock size={15} /> : <Ban size={15} />}
                <span>{user.is_blocked ? "Unblock" : "Block"}</span>
              </button>
            </article>
          ))}
        </div>
        <footer className="admin-pagination">
          <button disabled={offset === 0} title="Previous page" onClick={() => changePage(Math.max(0, offset - PAGE_SIZE))}><ChevronLeft size={17} /></button>
          <span>{users ? Math.floor(offset / PAGE_SIZE) + 1 : 1} / {Math.max(1, Math.ceil((users?.total ?? 0) / PAGE_SIZE))}</span>
          <button disabled={!users || offset + PAGE_SIZE >= users.total} title="Next page" onClick={() => changePage(offset + PAGE_SIZE)}><ChevronRight size={17} /></button>
        </footer>
      </section>
    </section>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}
