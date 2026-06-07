import type { Achievement, Stats, Task } from "../types/domain";

type Props = {
  tasks: Task[];
  achievements: Achievement[];
  stats: Stats | null;
};

export function DashboardPage({ tasks, achievements, stats }: Props) {
  const upcoming = tasks
    .filter((task) => task.status !== "done" && task.deadline)
    .sort((a, b) => String(a.deadline).localeCompare(String(b.deadline)))
    .slice(0, 5);

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Dashboard</h1>
          <p>Current workload, deadlines, and recent wins.</p>
        </div>
      </header>
      <div className="metrics-grid">
        <div className="metric"><span>Total tasks</span><strong>{stats?.total_tasks ?? 0}</strong></div>
        <div className="metric"><span>Completed</span><strong>{stats?.completed_tasks ?? 0}</strong></div>
        <div className="metric"><span>Completion rate</span><strong>{stats?.completion_rate ?? 0}%</strong></div>
        <div className="metric"><span>Streak</span><strong>{stats?.current_streak ?? 0}</strong></div>
      </div>
      <div className="two-column">
        <section className="panel">
          <h2>Upcoming</h2>
          {upcoming.length === 0 ? <p className="muted">No upcoming deadlines.</p> : upcoming.map((task) => (
            <article className="compact-row" key={task.id}>
              <span>{task.title}</span>
              <time>{task.deadline ? new Date(task.deadline).toLocaleDateString() : ""}</time>
            </article>
          ))}
        </section>
        <section className="panel">
          <h2>Recent achievements</h2>
          {achievements.slice(0, 5).map((achievement) => (
            <article className="compact-row" key={achievement.id}>
              <span>{achievement.title}</span>
              <time>{new Date(achievement.awarded_at).toLocaleDateString()}</time>
            </article>
          ))}
          {achievements.length === 0 && <p className="muted">Complete tasks to unlock achievements.</p>}
        </section>
      </div>
    </section>
  );
}
