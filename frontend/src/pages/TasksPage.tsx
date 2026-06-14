import {
  CalendarDays,
  Check,
  ChevronDown,
  CornerDownRight,
  Edit3,
  Globe2,
  Handshake,
  Lock,
  Plus,
  Save,
  Search,
  Trash2,
  X
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api/client";
import type { AccountabilityCommitment, Category, Person, Task, TaskPriority, TaskStatus } from "../types/domain";

type Props = {
  tasks: Task[];
  categories: Category[];
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
};

type TaskDraft = {
  title: string;
  description: string;
  priority: TaskPriority;
  status: TaskStatus;
  category_id: string;
  deadline: string;
  visibility: "private" | "public";
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
  const [deadline, setDeadline] = useState("");
  const [visibility, setVisibility] = useState<"private" | "public">("private");
  const [newCategory, setNewCategory] = useState("");
  const [editingCategoryId, setEditingCategoryId] = useState<string | null>(null);
  const [categoryName, setCategoryName] = useState("");
  const [editingTaskId, setEditingTaskId] = useState<string | null>(null);
  const [taskDraft, setTaskDraft] = useState<TaskDraft | null>(null);
  const [subtaskFor, setSubtaskFor] = useState<string | null>(null);
  const [subtaskTitle, setSubtaskTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [people, setPeople] = useState<Person[]>([]);
  const [commitments, setCommitments] = useState<AccountabilityCommitment[]>([]);
  const [partnerByTask, setPartnerByTask] = useState<Record<string, string>>({});

  async function loadAccountability() {
    const [nextPeople, nextCommitments] = await Promise.all([api.people(), api.commitments()]);
    setPeople(nextPeople.filter((person) => person.relationship_status === "friends"));
    setCommitments(nextCommitments);
  }

  useEffect(() => {
    loadAccountability().catch((error) =>
      onError(error instanceof Error ? error.message : "Unable to load accountability partners")
    );
  }, []);

  const childrenByParent = useMemo(() => {
    const map = new Map<string, Task[]>();
    tasks.filter((task) => task.parent_id).forEach((task) => {
      map.set(task.parent_id!, [...(map.get(task.parent_id!) ?? []), task]);
    });
    return map;
  }, [tasks]);

  const filtered = useMemo(() => {
    const search = query.toLowerCase();
    return tasks.filter((task) => !task.parent_id).filter((task) => {
      const children = childrenByParent.get(task.id) ?? [];
      const textMatches = `${task.title} ${task.description ?? ""}`.toLowerCase().includes(search)
        || children.some((child) => `${child.title} ${child.description ?? ""}`.toLowerCase().includes(search));
      return textMatches
        && (!categoryFilter || task.category_id === categoryFilter)
        && (!hideDone || task.status !== "done");
    });
  }, [tasks, childrenByParent, query, categoryFilter, hideDone]);

  async function submitTask(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await api.createTask({
        title,
        description,
        priority,
        deadline: deadline ? new Date(`${deadline}T23:59:00`).toISOString() : null,
        visibility,
        category_id: categoryId || null
      });
      setTitle("");
      setDescription("");
      setPriority("medium");
      setCategoryId("");
      setDeadline("");
      setVisibility("private");
      setComposerOpen(false);
      await onChanged();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to create task");
    } finally {
      setBusy(false);
    }
  }

  async function submitCategory(event: FormEvent) {
    event.preventDefault();
    if (!newCategory.trim()) return;
    await mutate(async () => {
      await api.createCategory(newCategory.trim());
      setNewCategory("");
    });
  }

  async function saveCategory(event: FormEvent) {
    event.preventDefault();
    if (!editingCategoryId || !categoryName.trim()) return;
    await mutate(async () => {
      await api.updateCategory(editingCategoryId, categoryName.trim());
      setEditingCategoryId(null);
      setCategoryName("");
    });
  }

  async function createSubtask(event: FormEvent, parent: Task) {
    event.preventDefault();
    if (!subtaskTitle.trim()) return;
    await mutate(async () => {
      await api.createTask({
        title: subtaskTitle.trim(),
        priority: parent.priority,
        visibility: parent.visibility,
        category_id: parent.category_id,
        parent_id: parent.id
      });
      setSubtaskTitle("");
      setSubtaskFor(null);
    });
  }

  function beginEdit(task: Task) {
    setEditingTaskId(task.id);
    setTaskDraft({
      title: task.title,
      description: task.description ?? "",
      priority: task.priority,
      status: task.status,
      category_id: task.category_id ?? "",
      deadline: task.deadline ? task.deadline.slice(0, 10) : "",
      visibility: task.visibility
    });
  }

  async function saveTask(event: FormEvent, task: Task) {
    event.preventDefault();
    if (!taskDraft) return;
    await mutate(async () => {
      await api.updateTask(task.id, {
        title: taskDraft.title,
        description: taskDraft.description || null,
        priority: taskDraft.priority,
        status: taskDraft.status,
        category_id: taskDraft.category_id || null,
        deadline: taskDraft.deadline ? new Date(`${taskDraft.deadline}T23:59:00`).toISOString() : null,
        visibility: taskDraft.visibility
      });
      setEditingTaskId(null);
      setTaskDraft(null);
    });
  }

  async function mutate(action: () => Promise<unknown>) {
    onError(null);
    try {
      await action();
      await Promise.all([onChanged(), loadAccountability()]);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update task");
    }
  }

  return (
    <section className="tasks-page">
      <header className="page-header">
        <div><h1>Tasks</h1><p>Organize the work that moves your goals forward.</p></div>
        <button aria-label={composerOpen ? "Close task form" : "Create new task"} className="primary-action" onClick={() => setComposerOpen((value) => !value)}>
          {composerOpen ? <X size={19} /> : <Plus size={19} />}<span>{composerOpen ? "Close" : "New task"}</span>
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
            <div className="form-row task-create-row">
              <select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
                <option value="low">Low priority</option><option value="medium">Medium priority</option><option value="high">High priority</option>
              </select>
              <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                <option value="">No category</option>
                {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
              </select>
              <label className="date-field"><CalendarDays size={15} /><input aria-label="Deadline" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} /></label>
              <button disabled={busy}>{busy ? "Creating..." : "Create task"}</button>
            </div>
          </form>
          <div className="category-manager">
            <form className="category-form" onSubmit={submitCategory}><input placeholder="New category" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} /><button title="Add category"><Plus size={16} /></button></form>
            <div className="category-list">
              {categories.map((category) => editingCategoryId === category.id ? (
                <form className="category-edit" onSubmit={saveCategory} key={category.id}>
                  <input value={categoryName} onChange={(event) => setCategoryName(event.target.value)} autoFocus />
                  <button title="Save category"><Save size={14} /></button>
                  <button type="button" title="Cancel" onClick={() => setEditingCategoryId(null)}><X size={14} /></button>
                </form>
              ) : (
                <span className="category-manage-chip" key={category.id}>
                  {category.name}
                  <button title={`Rename ${category.name}`} onClick={() => { setEditingCategoryId(category.id); setCategoryName(category.name); }}><Edit3 size={12} /></button>
                  <button title={`Delete ${category.name}`} onClick={() => void mutate(() => api.deleteCategory(category.id))}><X size={12} /></button>
                </span>
              ))}
            </div>
          </div>
        </section>
      )}

      <div className="task-toolbar">
        <label className="search-field"><Search size={17} /><input aria-label="Search tasks" placeholder="Search tasks and subtasks" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
        <label className="select-field"><select aria-label="Category filter" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option value="">All categories</option>{categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}</select><ChevronDown size={15} /></label>
        <label className="check-filter"><input type="checkbox" checked={hideDone} onChange={(event) => setHideDone(event.target.checked)} />Hide completed</label>
      </div>

      <section className="task-list">
        <div className="section-heading"><h2>All tasks</h2><span>{filtered.length} shown</span></div>
        {filtered.map((task) => (
          <div className="task-family" key={task.id}>
            <TaskCard
              task={task}
              categories={categories}
              commitment={commitments.find((item) => item.task_id === task.id && item.status !== "declined")}
              people={people}
              partnerId={partnerByTask[task.id] ?? ""}
              editing={editingTaskId === task.id}
              draft={editingTaskId === task.id ? taskDraft : null}
              onDraft={setTaskDraft}
              onEdit={() => beginEdit(task)}
              onCancelEdit={() => { setEditingTaskId(null); setTaskDraft(null); }}
              onSave={(event) => void saveTask(event, task)}
              onComplete={() => void mutate(() => api.completeTask(task.id))}
              onDelete={() => void mutate(() => api.deleteTask(task.id))}
              onPartner={(value) => setPartnerByTask((current) => ({ ...current, [task.id]: value }))}
              onInvite={() => void mutate(() => api.inviteAccountability(task.id, partnerByTask[task.id]))}
            />
            {((childrenByParent.get(task.id)?.length ?? 0) > 0 || task.status !== "done") && <div className="subtask-list">
              {(childrenByParent.get(task.id) ?? []).map((subtask) => (
                <TaskCard
                  compact
                  task={subtask}
                  categories={categories}
                  people={[]}
                  partnerId=""
                  editing={editingTaskId === subtask.id}
                  draft={editingTaskId === subtask.id ? taskDraft : null}
                  onDraft={setTaskDraft}
                  onEdit={() => beginEdit(subtask)}
                  onCancelEdit={() => { setEditingTaskId(null); setTaskDraft(null); }}
                  onSave={(event) => void saveTask(event, subtask)}
                  onComplete={() => void mutate(() => api.completeTask(subtask.id))}
                  onDelete={() => void mutate(() => api.deleteTask(subtask.id))}
                  onPartner={() => undefined}
                  onInvite={() => undefined}
                  key={subtask.id}
                />
              ))}
              {subtaskFor === task.id ? (
                <form className="subtask-form" onSubmit={(event) => void createSubtask(event, task)}>
                  <CornerDownRight size={16} />
                  <input placeholder="Describe the subtask" value={subtaskTitle} onChange={(event) => setSubtaskTitle(event.target.value)} autoFocus />
                  <button title="Add subtask"><Plus size={15} /></button>
                  <button type="button" title="Cancel" onClick={() => setSubtaskFor(null)}><X size={15} /></button>
                </form>
              ) : task.status !== "done" && (
                <button className="add-subtask" onClick={() => { setSubtaskFor(task.id); setSubtaskTitle(""); }}><CornerDownRight size={15} />Add subtask</button>
              )}
            </div>}
          </div>
        ))}
        {filtered.length === 0 && <div className="empty-state"><Check size={22} /><strong>No matching tasks</strong><p>Change the filters or create the next task.</p></div>}
      </section>
    </section>
  );
}

type TaskCardProps = {
  task: Task;
  categories: Category[];
  commitment?: AccountabilityCommitment;
  people: Person[];
  partnerId: string;
  editing: boolean;
  compact?: boolean;
  draft: TaskDraft | null;
  onDraft: (draft: TaskDraft) => void;
  onEdit: () => void;
  onCancelEdit: () => void;
  onSave: (event: FormEvent) => void;
  onComplete: () => void;
  onDelete: () => void;
  onPartner: (value: string) => void;
  onInvite: () => void;
};

function TaskCard(props: TaskCardProps) {
  const { task, categories, commitment, people, partnerId, editing, compact, draft } = props;
  const category = categories.find((item) => item.id === task.category_id);
  if (editing && draft) {
    return (
      <form className={`task-item task-edit-form ${compact ? "subtask-item" : ""}`} onSubmit={props.onSave}>
        <div className="task-edit-fields">
          <input value={draft.title} onChange={(event) => props.onDraft({ ...draft, title: event.target.value })} required />
          <textarea value={draft.description} placeholder="Description" onChange={(event) => props.onDraft({ ...draft, description: event.target.value })} />
          <select value={draft.priority} onChange={(event) => props.onDraft({ ...draft, priority: event.target.value as TaskPriority })}><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select>
          <select value={draft.status} onChange={(event) => props.onDraft({ ...draft, status: event.target.value as TaskStatus })}><option value="todo">To do</option><option value="in_progress">In progress</option><option value="done">Done</option></select>
          <select value={draft.category_id} onChange={(event) => props.onDraft({ ...draft, category_id: event.target.value })}><option value="">No category</option>{categories.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
          <input type="date" value={draft.deadline} onChange={(event) => props.onDraft({ ...draft, deadline: event.target.value })} />
          <select value={draft.visibility} onChange={(event) => props.onDraft({ ...draft, visibility: event.target.value as "private" | "public" })}><option value="private">Private</option><option value="public">Public</option></select>
        </div>
        <div className="task-edit-actions"><button title="Save"><Save size={15} /></button><button type="button" title="Cancel" onClick={props.onCancelEdit}><X size={15} /></button></div>
      </form>
    );
  }

  return (
    <article className={`task-item ${task.status} ${compact ? "subtask-item" : ""}`}>
      <button className="complete-control" title="Complete task" disabled={task.status === "done"} onClick={props.onComplete}><Check size={15} /></button>
      <div className="task-item-copy">
        <h3>{task.title}</h3>
        {task.description && <p>{task.description}</p>}
        <div className="task-meta">
          {category && <span className="category-chip">{category.name}</span>}
          <span className={`visibility-chip ${task.visibility}`}>{task.visibility === "public" ? <Globe2 size={11} /> : <Lock size={11} />}{task.visibility}</span>
          <span className={`priority-dot ${task.priority}`} />{task.status.replace("_", " ")}
          {task.deadline && <time><CalendarDays size={11} />{new Date(task.deadline).toLocaleDateString()}</time>}
        </div>
      </div>
      {!compact && <span className="xp-chip">+20 XP</span>}
      {commitment ? (
        <span className={`commitment-chip ${commitment.status}`} title={`Accountability with ${commitment.partner.display_name || commitment.partner.email}`}>
          <Handshake size={14} />{commitment.status}
        </span>
      ) : !compact && task.visibility === "public" && task.status !== "done" && people.length > 0 ? (
        <div className="accountability-invite">
          <select aria-label={`Accountability partner for ${task.title}`} value={partnerId} onChange={(event) => props.onPartner(event.target.value)}>
            <option value="">Partner</option>
            {people.map((person) => <option value={person.id} key={person.id}>{person.display_name || person.email.split("@")[0]}</option>)}
          </select>
          <button title="Invite accountability partner" disabled={!partnerId} onClick={props.onInvite}><Handshake size={15} /></button>
        </div>
      ) : null}
      <div className="task-row-actions">
        <button className="icon-button" title="Edit task" onClick={props.onEdit}><Edit3 size={15} /></button>
        <button className="icon-button danger-button" title="Delete task" onClick={props.onDelete}><Trash2 size={16} /></button>
      </div>
    </article>
  );
}
