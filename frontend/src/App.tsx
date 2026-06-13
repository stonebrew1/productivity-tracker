import { BarChart3, CheckSquare2, Flame, Home, LogOut, Trophy, Users, UsersRound, Zap } from "lucide-react";
import { useEffect, useState } from "react";

import { api, clearTokens, getAccessToken, setTokens } from "./api/client";
import { AchievementsPage } from "./pages/AchievementsPage";
import { AuthPage } from "./pages/AuthPage";
import { DashboardPage } from "./pages/DashboardPage";
import { GroupsPage } from "./pages/GroupsPage";
import { StatisticsPage } from "./pages/StatisticsPage";
import { SocialPage } from "./pages/SocialPage";
import { TasksPage } from "./pages/TasksPage";
import type { Achievement, Category, Stats, Task, User } from "./types/domain";

type View = "dashboard" | "tasks" | "social" | "groups" | "achievements" | "statistics";

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [view, setView] = useState<View>("dashboard");
  const [tasks, setTasks] = useState<Task[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));
  const [error, setError] = useState<string | null>(null);

  async function loadWorkspace() {
    setError(null);
    const [me, nextTasks, nextCategories, nextAchievements, nextStats] = await Promise.all([
      api.me(),
      api.tasks(),
      api.categories(),
      api.achievements(),
      api.statistics()
    ]);
    setUser(me);
    setTasks(nextTasks);
    setCategories(nextCategories);
    setAchievements(nextAchievements);
    setStats(nextStats);
  }

  useEffect(() => {
    if (!getAccessToken()) return;
    loadWorkspace().catch(() => clearTokens()).finally(() => setLoading(false));
  }, []);

  async function handleLogin(email: string, password: string, isRegister: boolean) {
    setError(null);
    if (isRegister) await api.register(email, password);
    const tokens = await api.login(email, password);
    setTokens(tokens);
    await loadWorkspace();
  }

  function handleLogout() {
    clearTokens();
    setUser(null);
    setTasks([]);
    setCategories([]);
    setAchievements([]);
    setStats(null);
  }

  async function refreshData() {
    try {
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to refresh data");
    }
  }

  if (loading) return <div className="loading">Loading workspace...</div>;
  if (!user) return <AuthPage onSubmit={handleLogin} error={error} setError={setError} />;

  const navItems = [
    { id: "dashboard" as View, label: "Today", icon: Home },
    { id: "tasks" as View, label: "Tasks", icon: CheckSquare2 },
    { id: "social" as View, label: "Social", icon: Users },
    { id: "groups" as View, label: "Groups", icon: UsersRound },
    { id: "achievements" as View, label: "Progress", icon: Trophy },
    { id: "statistics" as View, label: "Statistics", icon: BarChart3 }
  ];
  const displayName = user.display_name || user.email.split("@")[0];
  const level = stats?.level ?? 1;
  const xp = stats?.xp_total ?? 0;
  const streak = stats?.current_streak ?? 0;

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
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                aria-label={item.label}
                className={view === item.id ? "active" : ""}
                key={item.id}
                onClick={() => setView(item.id)}
                title={item.label}
              >
                <Icon size={18} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
        <div className="account">
          <button aria-label="Sign out" title="Sign out" onClick={handleLogout}><LogOut size={17} /><span>Sign out</span></button>
        </div>
      </aside>
      <div className="workspace">
        <header className="mobile-header">
          <div className="brand">
            <span className="brand-mark"><Zap size={18} fill="currentColor" /></span>
            <span className="brand-copy"><strong>Momentum</strong><small>{navItems.find((item) => item.id === view)?.label}</small></span>
          </div>
          <span className="mobile-streak"><Flame size={15} /> {streak}</span>
        </header>
        <main className="content">
          <div className="content-inner">
            {error && <div className="alert">{error}</div>}
            {view === "dashboard" && (
              <DashboardPage
                tasks={tasks}
                categories={categories}
                achievements={achievements}
                stats={stats}
                onChanged={refreshData}
                onError={setError}
              />
            )}
            {view === "tasks" && (
              <TasksPage
                tasks={tasks}
                categories={categories}
                onChanged={refreshData}
                onError={setError}
              />
            )}
            {view === "social" && <SocialPage onError={setError} />}
            {view === "groups" && <GroupsPage onError={setError} />}
            {view === "achievements" && <AchievementsPage onError={setError} />}
            {view === "statistics" && <StatisticsPage stats={stats} />}
          </div>
        </main>
        <nav className="mobile-nav" aria-label="Mobile navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                aria-label={item.label}
                className={view === item.id ? "active" : ""}
                key={item.id}
                onClick={() => setView(item.id)}
              >
                <Icon size={20} />
                <span>{item.label === "Gamification" ? "Progress" : item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
