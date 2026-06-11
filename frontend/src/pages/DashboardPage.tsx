import { CalendarClock, Check, Clock3, Globe2, Lock, Play, Plus, Star } from "lucide-react";
import { FormEvent, useMemo, useState } from "react";

import { api } from "../api/client";
import type { Achievement, Category, Stats, Task, TaskPriority } from "../types/domain";

type Props = {
  tasks: Task[];
  categories: Category[];
  achievements: Achievement[];
  stats: Stats | null;
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
};

export function DashboardPage({ tasks, categories, achievements, stats, onChanged, onError }: Props) {
  const today = dateKey(new Date());
  const weekEnd = new Date();
  weekEnd.setDate(weekEnd.getDate() + 7);
  const weekEndKey = dateKey(weekEnd);

  const activeTasks = tasks.filter((task) => task.status !== "done");
  const completedToday = tasks.filter(
    (task) => task.status === "done" && task.completed_at && dateKey(new Date(task.completed_at)) === today
  );
  const grouped = useMemo(() => groupTasks(activeTasks, today, weekEndKey), [tasks, today, weekEndKey]);
  const plannedMinutes = grouped.today.reduce((total, task) => total + (task.estimated_minutes ?? 0), 0);
  const dailyTotal = grouped.today.length + completedToday.length;
  const dailyProgress = dailyTotal ? Math.round((completedToday.length / dailyTotal) * 100) : 0;

  return (
    <section>
      <header className="page-header today-header">
        <div>
          <h1>Today</h1>
          <p>{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}</p>
        </div>
        <div className="today-score">
          <strong>{dailyProgress}%</strong>
          <span>daily plan</span>
        </div>
      </header>

      <QuickAdd categories={categories} onChanged={onChanged} onError={onError} />

      <div className="today-summary">
        <SummaryItem label="Completed today" value={completedToday.length} />
        <SummaryItem label="Remaining today" value={grouped.today.length} />
        <SummaryItem label="Planned effort" value={plannedMinutes ? `${plannedMinutes} min` : "Not set"} />
        <SummaryItem label="Current streak" value={stats?.current_streak ?? 0} />
      </div>

      <div className="today-layout">
        <div className="today-main">
          <TaskSection
            title="Overdue"
            tone="danger"
            tasks={grouped.overdue}
            categories={categories}
            empty="Nothing overdue."
            onChanged={onChanged}
            onError={onError}
          />
          <TaskSection
            title="Today"
            tasks={grouped.today}
            categories={categories}
            empty="Your day is clear. Add a focus task above."
            onChanged={onChanged}
            onError={onError}
          />
          <TaskSection
            title="Next 7 days"
            tasks={grouped.upcoming}
            categories={categories}
            empty="No scheduled work in the next seven days."
            onChanged={onChanged}
            onError={onError}
          />
        </div>

        <aside className="today-aside">
          <section className="panel">
            <h2>Latest achievement</h2>
            {achievements[0] ? (
              <div className="latest-achievement">
                <Star size={20} />
                <strong>{achievements[0].title}</strong>
                <p>{achievements[0].description}</p>
              </div>
            ) : (
              <p className="muted">Complete tasks to unlock achievements.</p>
            )}
          </section>
          <section className="panel">
            <h2>Workspace</h2>
            <div className="workspace-facts">
              <span><strong>{activeTasks.length}</strong> active tasks</span>
              <span><strong>{stats?.completion_rate ?? 0}%</strong> overall completion</span>
              <span><strong>{categories.length}</strong> categories</span>
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}

function QuickAdd({
  categories,
  onChanged,
  onError
}: {
  categories: Category[];
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
}) {
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [categoryId, setCategoryId] = useState("");
  const [scheduledFor, setScheduledFor] = useState(dateKey(new Date()));
  const [estimatedMinutes, setEstimatedMinutes] = useState(30);
  const [isFocus, setIsFocus] = useState(true);
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await api.createTask({
        title,
        priority,
        category_id: categoryId || null,
        scheduled_for: `${scheduledFor}T09:00:00`,
        estimated_minutes: estimatedMinutes,
        is_focus: isFocus,
        visibility
      });
      setTitle("");
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to add task");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="quick-add" onSubmit={submit}>
      <div className="quick-add-title">
        <Plus size={18} />
        <input
          aria-label="Task title"
          placeholder="What needs your attention?"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          required
        />
      </div>
      <select aria-label="Priority" value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
        <option value="high">High priority</option>
        <option value="medium">Medium priority</option>
        <option value="low">Low priority</option>
      </select>
      <select aria-label="Category" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
        <option value="">No category</option>
        {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
      </select>
      <input
        aria-label="Scheduled date"
        type="date"
        value={scheduledFor}
        onChange={(event) => setScheduledFor(event.target.value)}
      />
      <label className="estimate-input">
        <Clock3 size={15} />
        <input
          aria-label="Estimated minutes"
          type="number"
          min="5"
          max="1440"
          step="5"
          value={estimatedMinutes}
          onChange={(event) => setEstimatedMinutes(Number(event.target.value))}
        />
      </label>
      <label className="focus-toggle">
        <input type="checkbox" checked={isFocus} onChange={(event) => setIsFocus(event.target.checked)} />
        <Star size={16} />
      </label>
      <label className="visibility-toggle" title={visibility === "public" ? "Shared with followers" : "Private task"}>
        <input
          type="checkbox"
          checked={visibility === "public"}
          onChange={(event) => setVisibility(event.target.checked ? "public" : "private")}
        />
        {visibility === "public" ? <Globe2 size={16} /> : <Lock size={16} />}
      </label>
      <button disabled={busy}>{busy ? "Adding..." : "Add"}</button>
    </form>
  );
}

function TaskSection({
  title,
  tasks,
  categories,
  empty,
  tone,
  onChanged,
  onError
}: {
  title: string;
  tasks: Task[];
  categories: Category[];
  empty: string;
  tone?: "danger";
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
}) {
  return (
    <section className={`today-section ${tone ?? ""}`}>
      <header>
        <h2>{title}</h2>
        <span>{tasks.length}</span>
      </header>
      {tasks.length === 0 ? <p className="today-empty">{empty}</p> : tasks.map((task) => (
        <TodayTask
          task={task}
          category={categories.find((item) => item.id === task.category_id)}
          onChanged={onChanged}
          onError={onError}
          key={task.id}
        />
      ))}
    </section>
  );
}

function TodayTask({
  task,
  category,
  onChanged,
  onError
}: {
  task: Task;
  category?: Category;
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
}) {
  async function mutate(action: () => Promise<unknown>) {
    onError(null);
    try {
      await action();
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to update task");
    }
  }

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const taskDate = task.scheduled_for ?? task.deadline;

  return (
    <article className="today-task">
      <button className="complete-control" title="Complete task" onClick={() => mutate(() => api.completeTask(task.id))}>
        <Check size={16} />
      </button>
      <div className="today-task-copy">
        <div>
          <h3>{task.title}</h3>
          {task.is_focus && <Star className="focus-star" size={14} />}
        </div>
        <p>
          {category?.name ?? "Uncategorized"}
          {task.estimated_minutes ? ` · ${task.estimated_minutes} min` : ""}
          {taskDate ? ` · ${formatTaskDate(taskDate)}` : ""}
        </p>
      </div>
      <span className={`priority-mark ${task.priority}`}>{task.priority}</span>
      <div className="today-task-actions">
        {task.status === "todo" && (
          <button title="Start task" onClick={() => mutate(() => api.updateTask(task.id, { status: "in_progress" }))}>
            <Play size={15} />
          </button>
        )}
        <button
          title="Move to tomorrow"
          onClick={() => mutate(() => api.updateTask(task.id, { scheduled_for: `${dateKey(tomorrow)}T09:00:00` }))}
        >
          <CalendarClock size={15} />
        </button>
      </div>
    </article>
  );
}

function SummaryItem({ label, value }: { label: string; value: string | number }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}

function groupTasks(tasks: Task[], today: string, weekEnd: string) {
  const overdue: Task[] = [];
  const todayTasks: Task[] = [];
  const upcoming: Task[] = [];

  for (const task of tasks) {
    const planned = task.scheduled_for ? dateKey(new Date(task.scheduled_for)) : null;
    const deadline = task.deadline ? dateKey(new Date(task.deadline)) : null;
    const effectiveDate = planned ?? deadline;

    if (effectiveDate && effectiveDate < today) overdue.push(task);
    else if (effectiveDate === today || (!effectiveDate && task.is_focus)) todayTasks.push(task);
    else if (effectiveDate && effectiveDate > today && effectiveDate <= weekEnd) upcoming.push(task);
  }

  const sort = (a: Task, b: Task) =>
    Number(b.is_focus) - Number(a.is_focus)
    || priorityRank(b.priority) - priorityRank(a.priority)
    || String(a.scheduled_for ?? a.deadline).localeCompare(String(b.scheduled_for ?? b.deadline));

  return {
    overdue: overdue.sort(sort),
    today: todayTasks.sort(sort),
    upcoming: upcoming.sort(sort)
  };
}

function priorityRank(priority: TaskPriority) {
  return priority === "high" ? 3 : priority === "medium" ? 2 : 1;
}

function dateKey(value: Date) {
  const localDate = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

function formatTaskDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
