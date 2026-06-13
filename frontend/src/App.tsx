import { BarChart3, Bell, CheckSquare2, Flame, Home, LogOut, Trophy, Users, UsersRound, Zap } from "lucide-react";
import { useEffect, useState } from "react";
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from "react-router-dom";

import { api, clearTokens, setTokens, subscribeToSessionChanges } from "./api/client";
import { AchievementsPage } from "./pages/AchievementsPage";
import { AuthPage } from "./pages/AuthPage";
import { DashboardPage } from "./pages/DashboardPage";
import { GroupsPage } from "./pages/GroupsPage";
import { InboxPage } from "./pages/InboxPage";
import { StatisticsPage } from "./pages/StatisticsPage";
import { SocialPage } from "./pages/SocialPage";
import { TasksPage } from "./pages/TasksPage";
import { VerifyEmailPage } from "./pages/VerifyEmailPage";
import type { Achievement, Category, RegistrationResponse, Stats, Task, User } from "./types/domain";

const NAV_ITEMS: Array<{
  path: string;
  label: string;
  icon: typeof Home;
}> = [
  { path: "/today", label: "Today", icon: Home },
  { path: "/tasks", label: "Tasks", icon: CheckSquare2 },
  { path: "/social", label: "Social", icon: Users },
  { path: "/groups", label: "Groups", icon: UsersRound },
  { path: "/progress", label: "Progress", icon: Trophy },
  { path: "/statistics", label: "Statistics", icon: BarChart3 }
];

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const location = useLocation();
  const navigate = useNavigate();
  const isVerificationRoute = location.pathname === "/verify-email";

  async function loadWorkspace() {
    setError(null);
    const [me, nextTasks, nextCategories, nextAchievements, nextStats, nextNotifications] = await Promise.all([
      api.me(),
      api.tasks(),
      api.categories(),
      api.achievements(),
      api.statistics(),
      api.notifications()
    ]);
    setUser(me);
    setTasks(nextTasks);
    setCategories(nextCategories);
    setAchievements(nextAchievements);
    setStats(nextStats);
    setUnreadNotifications(nextNotifications.filter((notification) => !notification.is_read).length);
  }

  function resetWorkspaceState() {
    setUser(null);
    setTasks([]);
    setCategories([]);
    setAchievements([]);
    setStats(null);
    setUnreadNotifications(0);
  }

  function clearWorkspace() {
    clearTokens();
    resetWorkspaceState();
  }

  useEffect(() => {
    if (isVerificationRoute) {
      setLoading(false);
      return;
    }
    api.restoreSession()
      .then((restored) => restored ? loadWorkspace() : undefined)
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, [isVerificationRoute]);

  useEffect(() => {
    return subscribeToSessionChanges((tokens) => {
      setTokens(tokens);
      resetWorkspaceState();
      loadWorkspace().catch(() => {
        clearWorkspace();
        navigate("/login", { replace: true });
      });
    });
  }, [navigate]);

  useEffect(() => {
    if (!user) return;
    const refreshUnread = () => {
      api.notifications()
        .then((notifications) => setUnreadNotifications(notifications.filter((notification) => !notification.is_read).length))
        .catch(() => undefined);
    };
    const interval = window.setInterval(refreshUnread, 30_000);
    window.addEventListener("focus", refreshUnread);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener("focus", refreshUnread);
    };
  }, [user?.id]);

  async function handleVerifiedSession() {
    resetWorkspaceState();
    await loadWorkspace();
  }

  async function handleLogin(email: string, password: string) {
    setError(null);
    const tokens = await api.login(email, password);
    setTokens(tokens, true);
    await loadWorkspace();
    const requestedPath = (location.state as { from?: string } | null)?.from;
    navigate(requestedPath && requestedPath !== "/login" ? requestedPath : "/today", { replace: true });
  }

  async function handleRegister(
    displayName: string, email: string, password: string
  ): Promise<RegistrationResponse> {
    setError(null);
    return api.register(displayName, email, password);
  }

  async function handleLogout() {
    await api.logout().catch(() => undefined);
    clearWorkspace();
    navigate("/login", { replace: true });
  }

  async function refreshData() {
    try {
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh data");
    }
  }

  if (loading) return <div className="loading">Loading workspace...</div>;
  if (isVerificationRoute) {
    return (
      <Routes>
        <Route path="/verify-email" element={<VerifyEmailPage onVerified={handleVerifiedSession} />} />
      </Routes>
    );
  }
  if (!user) {
    return (
      <Routes>
        <Route
          path="/login"
          element={<AuthPage onLogin={handleLogin} onRegister={handleRegister} onResend={api.resendVerification} error={error} setError={setError} />}
        />
        <Route path="*" element={<Navigate to="/login" replace state={{ from: location.pathname }} />} />
      </Routes>
    );
  }

  const displayName = user.display_name || user.email.split("@")[0];
  const level = stats?.level ?? 1;
  const xp = stats?.xp_total ?? 0;
  const streak = stats?.current_streak ?? 0;
  const activeNav = NAV_ITEMS.find((item) =>
    item.path === "/groups"
      ? location.pathname.startsWith("/groups")
      : location.pathname === item.path
  );
  const activeLabel = location.pathname === "/inbox" ? "Inbox" : activeNav?.label ?? "Today";

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><Zap size={20} fill="currentColor" /></span>
          <span className="brand-copy"><strong>Momentum</strong></span>
        </div>
        <section className="sidebar-profile">
          <span className="account-avatar">{displayName.slice(0, 1).toUpperCase()}</span>
          <div><strong>{displayName}</strong><span>Level {level}</span></div>
          <span className="streak-pill"><Flame size={13} />{streak}</span>
        </section>
        <div className="sidebar-xp">
          <div><span>{xp} XP</span><span>Level {level}</span></div>
          <i><b style={{ width: `${stats ? Math.round((stats.xp_into_level / stats.xp_for_next_level) * 100) : 0}%` }} /></i>
        </div>
        <nav aria-label="Primary navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                aria-label={item.label}
                className={({ isActive }) => isActive ? "active" : ""}
                end={item.path !== "/groups"}
                key={item.path}
                title={item.label}
                to={item.path}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
        <div className="account">
          <button aria-label="Sign out" title="Sign out" onClick={() => void handleLogout()}><LogOut size={17} /><span>Sign out</span></button>
        </div>
      </aside>
      <div className="workspace">
        <header className="mobile-header">
          <div className="brand">
            <span className="brand-mark"><Zap size={18} fill="currentColor" /></span>
            <span className="brand-copy"><strong>Momentum</strong><small>{activeLabel}</small></span>
          </div>
          <span className="mobile-streak"><Flame size={15} /> {streak}</span>
          <InboxLink className="mobile-inbox" unread={unreadNotifications} />
        </header>
        <main className="content">
          <div className="content-inner">
            <div className="workspace-topbar">
              <InboxLink className="workspace-inbox" unread={unreadNotifications} />
            </div>
            {error && <div className="alert">{error}</div>}
            <Routes>
              <Route path="/" element={<Navigate to="/today" replace />} />
              <Route
                path="/today"
                element={<DashboardPage tasks={tasks} categories={categories} achievements={achievements} stats={stats} onChanged={refreshData} onError={setError} />}
              />
              <Route
                path="/tasks"
                element={<TasksPage tasks={tasks} categories={categories} onChanged={refreshData} onError={setError} />}
              />
              <Route path="/social" element={<SocialPage onError={setError} onUnreadChange={setUnreadNotifications} />} />
              <Route path="/groups" element={<GroupsPage onError={setError} />} />
              <Route path="/groups/:groupId" element={<GroupsPage onError={setError} />} />
              <Route path="/groups/:groupId/:section" element={<GroupsPage onError={setError} />} />
              <Route path="/progress" element={<AchievementsPage onError={setError} />} />
              <Route path="/statistics" element={<StatisticsPage stats={stats} />} />
              <Route path="/inbox" element={<InboxPage onError={setError} onUnreadChange={setUnreadNotifications} />} />
              <Route path="/login" element={<Navigate to="/today" replace />} />
              <Route path="*" element={<Navigate to="/today" replace />} />
            </Routes>
          </div>
        </main>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                aria-label={item.label}
                className={({ isActive }) => isActive ? "active" : ""}
                end={item.path !== "/groups"}
                key={item.path}
                to={item.path}
              >
                <Icon size={20} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </div>
    </div>
  );
}

function InboxLink({ className, unread }: { className: string; unread: number }) {
  return (
    <NavLink aria-label={unread > 0 ? `Inbox, ${unread} unread` : "Inbox"} className={className} title="Inbox" to="/inbox">
      <Bell size={18} />
      {unread > 0 && <b>{unread > 9 ? "9+" : unread}</b>}
    </NavLink>
  );
}
