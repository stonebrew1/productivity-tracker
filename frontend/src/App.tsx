import { BarChart3, CalendarDays, CheckCircle2, ListTodo, LogOut, Medal, Users } from "lucide-react";
import { useEffect, useState } from "react";

import { api, clearTokens, getAccessToken, setTokens } from "./api/client";
import { AchievementsPage } from "./pages/AchievementsPage";
import { AuthPage } from "./pages/AuthPage";
import { DashboardPage } from "./pages/DashboardPage";
import { StatisticsPage } from "./pages/StatisticsPage";
import { SocialPage } from "./pages/SocialPage";
import { TasksPage } from "./pages/TasksPage";
import type { Achievement, Category, Stats, Task, User } from "./types/domain";

type View = "dashboard" | "tasks" | "social" | "achievements" | "statistics";

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
    { id: "dashboard" as View, label: "Today", icon: CalendarDays },
    { id: "tasks" as View, label: "Tasks", icon: ListTodo },
    { id: "social" as View, label: "Social", icon: Users },
    { id: "achievements" as View, label: "Gamification", icon: Medal },
    { id: "statistics" as View, label: "Statistics", icon: BarChart3 }
  ];

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark"><CheckCircle2 size={22} /></span>
          <span className="brand-copy"><strong>Momentum</strong><small>Productivity network</small></span>
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
          <span className="account-avatar">{(user.display_name ?? user.email).slice(0, 1).toUpperCase()}</span>
          <span className="account-copy"><strong>{user.display_name || user.email.split("@")[0]}</strong><small>{user.email}</small></span>
          <button aria-label="Logout" title="Logout" onClick={handleLogout}>
            <LogOut size={16} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="mobile-header">
          <div className="brand">
            <span className="brand-mark"><CheckCircle2 size={20} /></span>
            <span className="brand-copy"><strong>Momentum</strong><small>{navItems.find((item) => item.id === view)?.label}</small></span>
          </div>
          <button aria-label="Logout" title="Logout" onClick={handleLogout}><LogOut size={18} /></button>
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
