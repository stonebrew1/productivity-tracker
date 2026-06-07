import { FormEvent, useState } from "react";
import { Check, Plus, Trash2 } from "lucide-react";

import { api } from "../api/client";
import type { Category, Task, TaskPriority } from "../types/domain";

type Props = {
  tasks: Task[];
  categories: Category[];
  onChanged: () => Promise<void>;
  onError: (message: string | null) => void;
};

export function TasksPage({ tasks, categories, onChanged, onError }: Props) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [categoryId, setCategoryId] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [busy, setBusy] = useState(false);

  async function submitTask(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      await api.createTask({
        title,
        description,
        priority,
        category_id: categoryId || null
      });
      setTitle("");
      setDescription("");
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

  async function complete(id: string) {
    try {
      await api.completeTask(id);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to complete task");
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteTask(id);
      await onChanged();
    } catch (err) {
      onError(err instanceof Error ? err.message : "Unable to delete task");
    }
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Tasks</h1>
          <p>Create, categorize, and complete personal work.</p>
        </div>
      </header>
      <div className="tasks-layout">
        <section className="panel">
          <h2>New task</h2>
          <form className="stack" onSubmit={submitTask}>
            <input placeholder="Task title" value={title} onChange={(event) => setTitle(event.target.value)} required />
            <textarea placeholder="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
            <select value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">No category</option>
              {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
            </select>
            <button disabled={busy}><Plus size={16} /> Add task</button>
          </form>
          <form className="inline-form" onSubmit={submitCategory}>
            <input placeholder="New category" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} />
            <button><Plus size={16} /></button>
          </form>
        </section>
        <section className="task-list">
          {tasks.map((task) => (
            <article className={`task-item ${task.status}`} key={task.id}>
              <div>
                <h2>{task.title}</h2>
                <p>{task.description || "No description"}</p>
                <span>{task.priority}</span>
              </div>
              <div className="task-actions">
                {task.status !== "done" && <button title="Complete task" onClick={() => complete(task.id)}><Check size={16} /></button>}
                <button title="Delete task" onClick={() => remove(task.id)}><Trash2 size={16} /></button>
              </div>
            </article>
          ))}
          {tasks.length === 0 && <p className="muted">No tasks yet.</p>}
        </section>
      </div>
    </section>
  );
}
