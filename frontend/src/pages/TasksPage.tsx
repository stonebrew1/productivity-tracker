import { Check, ChevronDown, Globe2, Handshake, Lock, Plus, Search, Trash2, X } from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { AccountabilityCommitment, Category, Person, Task, TaskPriority } from "../types/domain";

type Props = {
  tasks: Task[];
  categories: Category[];
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
};

export function TasksPage({ tasks, categories, onChanged, onError }: Props) {
  const [composerOpen, setComposerOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [hideDone, setHideDone] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [categoryId, setCategoryId] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [newCategory, setNewCategory] = useState("");
  const [busy, setBusy] = useState(false);
  const [people, setPeople] = useState<Person[]>([]);
  const [commitments, setCommitments] = useState<AccountabilityCommitment[]>([]);
  const [partnerByTask, setPartnerByTask] = useState<Record<string, string>>({});

  async function loadAccountability() {
    const [nextPeople, nextCommitments] = await Promise.all([api.people(), api.commitments()]);
    setPeople(nextPeople.filter((person) => person.is_following));
    setCommitments(nextCommitments);
  }

  useEffect(() => {
    loadAccountability().catch((error) =>
      onError(error instanceof Error ? error.message : "Unable to load accountability partners")
    );
  }, []);

  const filtered = useMemo(() => tasks.filter((task) => {
    const text = `${task.title} ${task.description ?? ""}`.toLowerCase();
    return text.includes(query.toLowerCase())
      && (!categoryFilter || task.category_id === categoryFilter)
      && (!hideDone || task.status !== "done");
  }), [tasks, query, categoryFilter, hideDone]);

  async function submitTask(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await api.createTask({
        title,
        description,
        priority,
        visibility,
        category_id: categoryId || null
      });
      setTitle("");
      setDescription("");
      setComposerOpen(false);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to create task");
    } finally {
      setBusy(false);
    }
  }

  async function submitCategory(event: FormEvent) {
    event.preventDefault();
    if (!newCategory.trim()) return;
    try {
      await api.createCategory(newCategory.trim());
      setNewCategory("");
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to create category");
    }
  }

  async function mutate(action: () => Promise<unknown>) {
    try {
      await action();
      await Promise.all([onChanged(), loadAccountability()]);
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to update task");
    }
  }

  return (
    <section className="tasks-page">
      <header className="page-header">
        <div><h1>Tasks</h1><p>Organize the work that moves your goals forward.</p></div>
        <button
          aria-label={composerOpen ? "Close task form" : "Create new task"}
          className="primary-action"
          onClick={() => setComposerOpen((value) => !value)}
        >
          {composerOpen ? <X size={19} /> : <Plus size={19} />}
          <span>{composerOpen ? "Close" : "New task"}</span>
        </button>
      </header>

      {composerOpen && (
        <section className="panel task-composer">
          <div className="section-heading"><h2>Create task</h2><span>Keep the next action clear</span></div>
          <form className="task-form" onSubmit={submitTask}>
            <input placeholder="What needs to be done?" value={title} onChange={(event) => setTitle(event.target.value)} required />
            <textarea placeholder="Add context or a useful definition of done" value={description} onChange={(event) => setDescription(event.target.value)} />
            <div className="visibility-field">
              <span>Visibility</span>
              <div className="visibility-segment" role="group" aria-label="Task visibility">
                <button className={visibility === "private" ? "active" : ""} type="button" onClick={() => setVisibility("private")}><Lock size={15} />Private</button>
                <button className={visibility === "public" ? "active public" : ""} type="button" onClick={() => setVisibility("public")}><Globe2 size={15} />Public</button>
              </div>
              <small>{visibility === "public" ? "Appears in Social and contributes to joined challenges." : "Visible only to you."}</small>
            </div>
            <div className="form-row">
              <select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
                <option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option>
              </select>
              <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                <option value="">No category</option>
                {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
              </select>
              <button disabled={busy}>{busy ? "Creating..." : "Create task"}</button>
            </div>
          </form>
          <form className="category-form" onSubmit={submitCategory}><input placeholder="New category" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} /><button title="Add category"><Plus size={16} /></button></form>
        </section>
      )}

      <div className="task-toolbar">
        <label className="search-field"><Search size={17} /><input aria-label="Search tasks" placeholder="Search tasks" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        <label className="select-field"><select aria-label="Category filter" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select><ChevronDown size={15} /></label>
        <label className="check-filter"><input type="checkbox" checked={hideDone} onChange={(event) => setHideDone(event.target.checked)} />Hide completed</label>
      </div>

      <section className="task-list">
        <div className="section-heading"><h2>All tasks</h2><span>{filtered.length} shown</span></div>
        {filtered.map((task) => {
          const category = categories.find((item) => item.id === task.category_id);
          const commitment = commitments.find((item) => item.task_id === task.id && item.status !== "declined");
          return (
            <article className={`task-item ${task.status}`} key={task.id}>
              <button className="complete-control" title="Complete task" disabled={task.status === "done"} onClick={() => mutate(() => api.completeTask(task.id))}><Check size={15} /></button>
              <div className="task-item-copy">
                <h3>{task.title}</h3>
                {task.description && <p>{task.description}</p>}
                <div className="task-meta">
                  {category && <span className="category-chip">{category.name}</span>}
                  <span className={`visibility-chip ${task.visibility}`}>{task.visibility === "public" ? <Globe2 size={11} /> : <Lock size={11} />}{task.visibility}</span>
                  <span className={`priority-dot ${task.priority}`} />{task.status.replace("_", " ")}
                </div>
              </div>
              <span className="xp-chip">+20 XP</span>
              {commitment ? (
                <span className={`commitment-chip ${commitment.status}`} title={`Accountability with ${commitment.partner.display_name || commitment.partner.email}`}>
                  <Handshake size={14} />{commitment.status}
                </span>
              ) : task.visibility === "public" && task.status !== "done" && people.length > 0 ? (
                <div className="accountability-invite">
                  <select
                    aria-label={`Accountability partner for ${task.title}`}
                    value={partnerByTask[task.id] ?? ""}
                    onChange={(event) => setPartnerByTask((value) => ({ ...value, [task.id]: event.target.value }))}
                  >
                    <option value="">Partner</option>
                    {people.map((person) => <option value={person.id} key={person.id}>{person.display_name || person.email.split("@")[0]}</option>)}
                  </select>
                  <button
                    title="Invite accountability partner"
                    disabled={!partnerByTask[task.id]}
                    onClick={() => mutate(() => api.inviteAccountability(task.id, partnerByTask[task.id]))}
                  ><Handshake size={15} /></button>
                </div>
              ) : null}
              <button className="icon-button danger-button" title="Delete task" onClick={() => mutate(() => api.deleteTask(task.id))}><Trash2 size={16} /></button>
            </article>
          );
        })}
        {filtered.length === 0 && <div className="empty-state"><Check size={22} /><strong>No matching tasks</strong><p>Change the filters or create the next task.</p></div>}
      </section>
    </section>
  );
}
