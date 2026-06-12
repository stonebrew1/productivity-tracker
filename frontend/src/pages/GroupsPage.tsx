import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors
} from "@dnd-kit/core";
import { CalendarDays, Check, CheckCircle2, Circle, ClipboardList, Copy, Crown, GripVertical, KeyRound, LoaderCircle, Plus, RefreshCw, Shield, Trash2, UserPlus, UsersRound, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { GroupInvitation, GroupTask, Person, ProductivityGroup, TaskPriority, TaskStatus } from "../types/domain";

const TASK_COLUMNS = [
  ["todo", "To do", Circle],
  ["in_progress", "In progress", LoaderCircle],
  ["done", "Done", CheckCircle2]
] as const;

export function GroupsPage({ onError }: { onError: (message: string | null) => void }) {
  const [groups, setGroups] = useState<ProductivityGroup[]>([]);
  const [invitations, setInvitations] = useState<GroupInvitation[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [inviteUserId, setInviteUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [tasks, setTasks] = useState<GroupTask[]>([]);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskPriority, setTaskPriority] = useState<TaskPriority>("medium");
  const [taskDeadline, setTaskDeadline] = useState("");
  const [taskAssignee, setTaskAssignee] = useState("");
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const dragSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  async function loadGroups(preferredId?: string) {
    const [nextGroups, nextInvitations, nextPeople] = await Promise.all([
      api.groups(),
      api.groupInvitations(),
      api.people()
    ]);
    setGroups(nextGroups);
    setInvitations(nextInvitations);
    setPeople(nextPeople.filter((person) => person.is_following));
    const nextSelected = preferredId ?? selectedId ?? nextGroups[0]?.id ?? null;
    setSelectedId(nextGroups.some((group) => group.id === nextSelected) ? nextSelected : nextGroups[0]?.id ?? null);
  }

  useEffect(() => {
    loadGroups().catch((error) =>
      onError(error instanceof Error ? error.message : "Unable to load groups")
    );
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTasks([]);
      return;
    }
    api.groupTasks(selectedId)
      .then(setTasks)
      .catch((error) => onError(error instanceof Error ? error.message : "Unable to load group tasks"));
  }, [selectedId]);

  async function mutate(action: () => Promise<unknown>, preferredId?: string) {
    setBusy(true);
    onError(null);
    try {
      await action();
      await loadGroups(preferredId);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update group");
    } finally {
      setBusy(false);
    }
  }

  async function submitCreate(event: FormEvent) {
    event.preventDefault();
    let createdId = "";
    await mutate(async () => {
      const group = await api.createGroup({ name, description: description || null });
      createdId = group.id;
      setName("");
      setDescription("");
    }, createdId);
    if (createdId) setSelectedId(createdId);
  }

  async function submitJoin(event: FormEvent) {
    event.preventDefault();
    let joinedId = "";
    await mutate(async () => {
      const group = await api.joinGroup(joinCode);
      joinedId = group.id;
      setJoinCode("");
    }, joinedId);
    if (joinedId) setSelectedId(joinedId);
  }

  async function refreshTasks(groupId = selectedId) {
    if (!groupId) return;
    setTasks(await api.groupTasks(groupId));
  }

  async function submitGroupTask(event: FormEvent) {
    event.preventDefault();
    if (!selected || !taskAssignee) return;
    setBusy(true);
    onError(null);
    try {
      await api.createGroupTask(selected.id, {
        title: taskTitle,
        description: taskDescription || null,
        priority: taskPriority,
        deadline: taskDeadline ? new Date(`${taskDeadline}T23:59:59`).toISOString() : null,
        assigned_to_id: taskAssignee
      });
      setTaskTitle("");
      setTaskDescription("");
      setTaskPriority("medium");
      setTaskDeadline("");
      await refreshTasks(selected.id);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to create group task");
    } finally {
      setBusy(false);
    }
  }

  async function changeTask(taskId: string, payload: { status?: TaskStatus; assigned_to_id?: string }) {
    setBusy(true);
    onError(null);
    try {
      await api.updateGroupTask(taskId, payload);
      await refreshTasks();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update group task");
    } finally {
      setBusy(false);
    }
  }

  async function moveTask(taskId: string, status: TaskStatus) {
    const current = tasks.find((task) => task.id === taskId);
    if (!current || !current.can_update_status || current.status === status) return;
    const previousTasks = tasks;
    setTasks((items) => items.map((task) => task.id === taskId ? { ...task, status } : task));
    onError(null);
    try {
      const updated = await api.updateGroupTask(taskId, { status });
      setTasks((items) => items.map((task) => task.id === taskId ? updated : task));
    } catch (error) {
      setTasks(previousTasks);
      onError(error instanceof Error ? error.message : "Unable to move group task");
    }
  }

  function handleDragEnd(event: DragEndEvent) {
    setActiveTaskId(null);
    const destination = event.over?.id as TaskStatus | undefined;
    if (!destination || !TASK_COLUMNS.some(([status]) => status === destination)) return;
    void moveTask(String(event.active.id), destination);
  }

  async function removeTask(taskId: string) {
    setBusy(true);
    onError(null);
    try {
      await api.deleteGroupTask(taskId);
      await refreshTasks();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to delete group task");
    } finally {
      setBusy(false);
    }
  }

  const selected = groups.find((group) => group.id === selectedId) ?? null;
  const eligiblePeople = people.filter(
    (person) => !selected?.members.some((member) => member.user_id === person.id)
  );

  async function copyCode() {
    if (!selected?.invite_code) return;
    try {
      await navigator.clipboard.writeText(selected.invite_code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      onError("Unable to copy the join code.");
    }
  }

  return (
    <section className="groups-page">
      <header className="page-header">
        <div><h1>Groups</h1><p>Create a team space, invite participants, and build shared momentum.</p></div>
        <span className="header-stat"><strong>{groups.length}</strong> workspaces</span>
      </header>

      {invitations.length > 0 && (
        <section className="group-invitations">
          <div className="section-heading"><h2>Invitations</h2><span>{invitations.length} pending</span></div>
          {invitations.map((invitation) => (
            <article key={invitation.id}>
              <span className="group-icon"><UsersRound size={18} /></span>
              <div><strong>{invitation.group_name}</strong><p>{invitation.inviter_name} invited you to join.</p></div>
              <div>
                <button title="Accept invitation" onClick={() => mutate(() => api.acceptGroupInvitation(invitation.id), invitation.group_id)}><Check size={15} /></button>
                <button title="Decline invitation" onClick={() => mutate(() => api.declineGroupInvitation(invitation.id))}><X size={15} /></button>
              </div>
            </article>
          ))}
        </section>
      )}

      <div className="groups-layout">
        <aside className="groups-sidebar">
          <section className="group-list-panel">
            <div className="section-heading"><h2>Your groups</h2><span>{groups.length}</span></div>
            {groups.map((group) => (
              <button className={selectedId === group.id ? "active" : ""} onClick={() => setSelectedId(group.id)} key={group.id}>
                <span className="group-icon"><UsersRound size={17} /></span>
                <span><strong>{group.name}</strong><small>{group.member_count} members</small></span>
                {group.role === "leader" && <Crown size={14} />}
              </button>
            ))}
            {groups.length === 0 && <p className="muted compact-copy">Create a group or join one with a code.</p>}
          </section>

          <section className="group-actions-panel">
            <form onSubmit={submitCreate}>
              <h2>Create group</h2>
              <input placeholder="Group name" value={name} onChange={(event) => setName(event.target.value)} required />
              <textarea placeholder="Purpose or shared goal" value={description} onChange={(event) => setDescription(event.target.value)} />
              <button disabled={busy}><Plus size={15} />Create</button>
            </form>
            <div className="group-action-divider"><span>or</span></div>
            <form onSubmit={submitJoin}>
              <h2>Join with code</h2>
              <input className="code-input" placeholder="ABCD2345" maxLength={12} value={joinCode} onChange={(event) => setJoinCode(event.target.value.toUpperCase())} required />
              <button disabled={busy}><KeyRound size={15} />Join group</button>
            </form>
          </section>
        </aside>

        <main className="group-detail">
          {!selected ? (
            <div className="empty-state"><UsersRound size={23} /><strong>No group selected</strong><p>Create or join a group to open its workspace.</p></div>
          ) : (
            <>
              <section className="group-hero">
                <span className="group-icon large"><UsersRound size={24} /></span>
                <div><span>{selected.role === "leader" ? "You lead this group" : "Member workspace"}</span><h2>{selected.name}</h2><p>{selected.description || "No group description yet."}</p></div>
                <div className="group-hero-stat"><strong>{selected.member_count}</strong><span>members</span></div>
              </section>

              {selected.role === "leader" && (
                <section className="leader-tools">
                  <div className="section-heading"><h2>Leader tools</h2><span><Shield size={13} /> Leader only</span></div>
                  <div className="leader-tool-grid">
                    <div className="invite-code-box">
                      <span>Join code</span>
                      <strong>{selected.invite_code}</strong>
                      <div>
                        <button title="Copy join code" onClick={copyCode}>{copied ? <Check size={15} /> : <Copy size={15} />}</button>
                        <button title="Generate a new code" onClick={() => mutate(() => api.rotateGroupCode(selected.id), selected.id)}><RefreshCw size={15} /></button>
                      </div>
                    </div>
                    <div className="direct-invite">
                      <span>Invite a connection</span>
                      <select value={inviteUserId} onChange={(event) => setInviteUserId(event.target.value)}>
                        <option value="">Choose person</option>
                        {eligiblePeople.map((person) => <option value={person.id} key={person.id}>{person.display_name || person.email.split("@")[0]}</option>)}
                      </select>
                      <button disabled={!inviteUserId || busy} onClick={() => mutate(async () => {
                        await api.inviteGroupMember(selected.id, inviteUserId);
                        setInviteUserId("");
                      }, selected.id)}><UserPlus size={15} />Invite</button>
                    </div>
                  </div>
                </section>
              )}

              <section className="group-work">
                <div className="section-heading">
                  <h2>Shared tasks</h2>
                  <span>{tasks.filter((task) => task.status === "done").length} / {tasks.length} complete</span>
                </div>

                {selected.role === "leader" && (
                  <form className="group-task-form" onSubmit={submitGroupTask}>
                    <div>
                      <label>Task</label>
                      <input placeholder="Define the next concrete result" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} required />
                    </div>
                    <div>
                      <label>Assign to</label>
                      <select value={taskAssignee} onChange={(event) => setTaskAssignee(event.target.value)} required>
                        <option value="">Choose participant</option>
                        {selected.members.map((member) => <option value={member.user_id} key={member.user_id}>{member.display_name || member.email.split("@")[0]}</option>)}
                      </select>
                    </div>
                    <div>
                      <label>Priority</label>
                      <select value={taskPriority} onChange={(event) => setTaskPriority(event.target.value as TaskPriority)}>
                        <option value="low">Low</option>
                        <option value="medium">Medium</option>
                        <option value="high">High</option>
                      </select>
                    </div>
                    <div>
                      <label>Due date</label>
                      <input type="date" value={taskDeadline} onChange={(event) => setTaskDeadline(event.target.value)} />
                    </div>
                    <div className="group-task-description">
                      <label>Details</label>
                      <input placeholder="Optional context or acceptance criteria" value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} />
                    </div>
                    <button disabled={busy}><Plus size={15} />Assign task</button>
                  </form>
                )}

                <DndContext
                  sensors={dragSensors}
                  onDragStart={(event) => setActiveTaskId(String(event.active.id))}
                  onDragCancel={() => setActiveTaskId(null)}
                  onDragEnd={handleDragEnd}
                >
                  <div className="group-task-board">
                    {TASK_COLUMNS.map(([status, label, Icon]) => (
                      <GroupTaskColumn
                        icon={Icon}
                        key={status}
                        label={label}
                        members={selected.members}
                        onAssigneeChange={(taskId, assignedToId) => changeTask(taskId, { assigned_to_id: assignedToId })}
                        onDelete={removeTask}
                        onStatusChange={(taskId, nextStatus) => changeTask(taskId, { status: nextStatus })}
                        status={status}
                        tasks={tasks.filter((task) => task.status === status)}
                      />
                    ))}
                  </div>
                  <DragOverlay>
                    {activeTaskId && tasks.find((task) => task.id === activeTaskId)
                      ? <GroupTaskPreview task={tasks.find((task) => task.id === activeTaskId)!} />
                      : null}
                  </DragOverlay>
                </DndContext>
              </section>

              <section className="group-roster">
                <div className="section-heading"><h2>Participants</h2><span>{selected.member_count} total</span></div>
                {selected.members.map((member) => (
                  <article key={member.user_id}>
                    <span className="avatar">{(member.display_name ?? member.email).slice(0, 1).toUpperCase()}</span>
                    <div><strong>{member.display_name || member.email.split("@")[0]}</strong><span>Level {member.level} - Joined {new Date(member.joined_at).toLocaleDateString()}</span></div>
                    <span className={`member-role ${member.role}`}>{member.role === "leader" ? <Crown size={12} /> : null}{member.role}</span>
                  </article>
                ))}
              </section>

            </>
          )}
        </main>
      </div>
    </section>
  );
}

type GroupTaskColumnProps = {
  icon: typeof Circle;
  label: string;
  members: ProductivityGroup["members"];
  onAssigneeChange: (taskId: string, assignedToId: string) => void;
  onDelete: (taskId: string) => void;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  status: TaskStatus;
  tasks: GroupTask[];
};

function GroupTaskColumn({
  icon: Icon,
  label,
  members,
  onAssigneeChange,
  onDelete,
  onStatusChange,
  status,
  tasks
}: GroupTaskColumnProps) {
  const { isOver, setNodeRef } = useDroppable({ id: status });

  return (
    <section className={`group-task-column ${status} ${isOver ? "drag-over" : ""}`} ref={setNodeRef}>
      <header><span><Icon size={14} />{label}</span><b>{tasks.length}</b></header>
      <div>
        {tasks.map((task) => (
          <DraggableGroupTask
            key={task.id}
            members={members}
            onAssigneeChange={onAssigneeChange}
            onDelete={onDelete}
            onStatusChange={onStatusChange}
            task={task}
          />
        ))}
        {tasks.length === 0 && <div className="group-task-empty"><ClipboardList size={17} /><span>No tasks</span></div>}
      </div>
    </section>
  );
}

function DraggableGroupTask({
  members,
  onAssigneeChange,
  onDelete,
  onStatusChange,
  task
}: {
  members: ProductivityGroup["members"];
  onAssigneeChange: (taskId: string, assignedToId: string) => void;
  onDelete: (taskId: string) => void;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  task: GroupTask;
}) {
  const { attributes, isDragging, listeners, setNodeRef } = useDraggable({
    id: task.id,
    disabled: !task.can_update_status
  });

  return (
    <article className={`group-task-card ${isDragging ? "dragging" : ""}`} ref={setNodeRef}>
      <div className="group-task-card-title">
        <i className={`priority-dot ${task.priority}`} />
        <strong>{task.title}</strong>
        {task.can_update_status && (
          <button
            aria-label={`Move ${task.title}`}
            className="group-task-drag-handle"
            title="Drag to change status"
            type="button"
            {...attributes}
            {...listeners}
          >
            <GripVertical size={15} />
          </button>
        )}
      </div>
      {task.description && <p>{task.description}</p>}
      <div className="group-task-meta">
        <span><UserPlus size={12} />{task.assignee_name}</span>
        {task.deadline && <span><CalendarDays size={12} />{new Date(task.deadline).toLocaleDateString()}</span>}
      </div>
      {task.can_manage && (
        <select aria-label={`Assignee for ${task.title}`} value={task.assigned_to_id} onChange={(event) => onAssigneeChange(task.id, event.target.value)}>
          {members.map((member) => <option value={member.user_id} key={member.user_id}>{member.display_name || member.email.split("@")[0]}</option>)}
        </select>
      )}
      <footer>
        {task.can_update_status ? (
          <select aria-label={`Status for ${task.title}`} value={task.status} onChange={(event) => onStatusChange(task.id, event.target.value as TaskStatus)}>
            <option value="todo">To do</option>
            <option value="in_progress">In progress</option>
            <option value="done">Done</option>
          </select>
        ) : <span>Assigned to {task.assignee_name}</span>}
        {task.can_manage && <button title="Delete group task" type="button" onClick={() => onDelete(task.id)}><Trash2 size={14} /></button>}
      </footer>
    </article>
  );
}

function GroupTaskPreview({ task }: { task: GroupTask }) {
  return (
    <article className="group-task-card drag-preview">
      <div className="group-task-card-title">
        <i className={`priority-dot ${task.priority}`} />
        <strong>{task.title}</strong>
        <GripVertical size={15} />
      </div>
      <div className="group-task-meta"><span><UserPlus size={12} />{task.assignee_name}</span></div>
    </article>
  );
}
