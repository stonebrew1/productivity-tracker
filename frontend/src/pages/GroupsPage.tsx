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
import { Activity, AlertTriangle, Award, BarChart3, CalendarDays, Check, CheckCircle2, Circle, ClipboardList, Clock3, Copy, Crown, Flag, Flame, Gauge, GripVertical, Heart, KeyRound, LayoutDashboard, LoaderCircle, Lock, Medal, MessageCircle, Pencil, Plus, RefreshCw, Save, Send, Shield, Target, Trash2, Trophy, UserPlus, UsersRound, X, Zap } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api } from "../api/client";
import type { GroupAchievement, GroupActivity, GroupAnalytics, GroupChallenge, GroupInvitation, GroupMilestone, GroupProgress, GroupTask, Person, ProductivityGroup, TaskPriority, TaskStatus } from "../types/domain";

const TASK_COLUMNS = [
  ["todo", "To do", Circle],
  ["in_progress", "In progress", LoaderCircle],
  ["done", "Done", CheckCircle2]
] as const;

type GroupSection = "overview" | "tasks" | "milestones" | "challenges" | "activity" | "members";

const GROUP_SECTIONS = [
  ["overview", "Overview", LayoutDashboard],
  ["tasks", "Tasks", ClipboardList],
  ["milestones", "Milestones", Flag],
  ["challenges", "Challenges", Target],
  ["activity", "Activity", Activity],
  ["members", "Members", UsersRound]
] as const;

export function GroupsPage({ onError }: { onError: (message: string | null) => void }) {
  const { groupId, section } = useParams();
  const navigate = useNavigate();
  const [groups, setGroups] = useState<ProductivityGroup[]>([]);
  const [invitations, setInvitations] = useState<GroupInvitation[]>([]);
  const [people, setPeople] = useState<Person[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [joinCode, setJoinCode] = useState("");
  const [inviteUserId, setInviteUserId] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const [tasks, setTasks] = useState<GroupTask[]>([]);
  const [milestones, setMilestones] = useState<GroupMilestone[]>([]);
  const [progress, setProgress] = useState<GroupProgress | null>(null);
  const [activity, setActivity] = useState<GroupActivity[]>([]);
  const [analytics, setAnalytics] = useState<GroupAnalytics | null>(null);
  const [challenges, setChallenges] = useState<GroupChallenge[]>([]);
  const [achievements, setAchievements] = useState<GroupAchievement[]>([]);
  const [challengeTitle, setChallengeTitle] = useState("");
  const [challengeDescription, setChallengeDescription] = useState("");
  const [challengeTarget, setChallengeTarget] = useState("3");
  const [challengeReward, setChallengeReward] = useState("75");
  const [challengeDeadline, setChallengeDeadline] = useState("");
  const [updateDraft, setUpdateDraft] = useState("");
  const [commentDrafts, setCommentDrafts] = useState<Record<string, string>>({});
  const [openActivityId, setOpenActivityId] = useState<string | null>(null);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskPriority, setTaskPriority] = useState<TaskPriority>("medium");
  const [taskDeadline, setTaskDeadline] = useState("");
  const [taskAssignee, setTaskAssignee] = useState("");
  const [taskMilestone, setTaskMilestone] = useState("");
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const [milestoneDescription, setMilestoneDescription] = useState("");
  const [milestoneDate, setMilestoneDate] = useState("");
  const [editingMilestoneId, setEditingMilestoneId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const dragSensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );
  const selectedId = groupId ?? null;
  const groupSection: GroupSection = GROUP_SECTIONS.some(([id]) => id === section)
    ? section as GroupSection
    : "overview";

  async function loadGroups(preferredId?: string) {
    const [nextGroups, nextInvitations, nextPeople] = await Promise.all([
      api.groups(),
      api.groupInvitations(),
      api.people()
    ]);
    setGroups(nextGroups);
    setInvitations(nextInvitations);
    setPeople(nextPeople.filter((person) => person.is_following));
    const requestedId = preferredId ?? groupId;
    const nextSelected = nextGroups.some((group) => group.id === requestedId)
      ? requestedId
      : nextGroups[0]?.id;
    if (nextSelected && (groupId !== nextSelected || section !== groupSection)) {
      navigate(`/groups/${nextSelected}/${preferredId ? "overview" : groupSection}`, { replace: true });
    } else if (!nextSelected && (groupId || section)) {
      navigate("/groups", { replace: true });
    }
  }

  useEffect(() => {
    loadGroups().catch((error) =>
      onError(error instanceof Error ? error.message : "Unable to load groups")
    );
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setTasks([]);
      setMilestones([]);
      setProgress(null);
      setActivity([]);
      setAnalytics(null);
      setChallenges([]);
      setAchievements([]);
      return;
    }
    api.groupProgress(selectedId)
      .then(async (nextProgress) => {
        const [nextTasks, nextMilestones, nextActivity, nextAnalytics, nextChallenges, nextAchievements] = await Promise.all([
          api.groupTasks(selectedId),
          api.groupMilestones(selectedId),
          api.groupActivity(selectedId),
          api.groupAnalytics(selectedId),
          api.groupChallenges(selectedId),
          api.groupAchievements(selectedId)
        ]);
        setTasks(nextTasks);
        setMilestones(nextMilestones);
        setProgress(nextProgress);
        setActivity(nextActivity);
        setAnalytics(nextAnalytics);
        setChallenges(nextChallenges);
        setAchievements(nextAchievements);
      })
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
    if (createdId) navigate(`/groups/${createdId}/overview`);
  }

  async function submitJoin(event: FormEvent) {
    event.preventDefault();
    let joinedId = "";
    await mutate(async () => {
      const group = await api.joinGroup(joinCode);
      joinedId = group.id;
      setJoinCode("");
    }, joinedId);
    if (joinedId) navigate(`/groups/${joinedId}/overview`);
  }

  async function refreshTasks(groupId = selectedId) {
    if (!groupId) return;
    const nextProgress = await api.groupProgress(groupId);
    const [nextTasks, nextMilestones, nextActivity, nextAnalytics, nextChallenges, nextAchievements] = await Promise.all([
      api.groupTasks(groupId),
      api.groupMilestones(groupId),
      api.groupActivity(groupId),
      api.groupAnalytics(groupId),
      api.groupChallenges(groupId),
      api.groupAchievements(groupId)
    ]);
    setTasks(nextTasks);
    setMilestones(nextMilestones);
    setProgress(nextProgress);
    setActivity(nextActivity);
    setAnalytics(nextAnalytics);
    setChallenges(nextChallenges);
    setAchievements(nextAchievements);
  }

  async function submitChallenge(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !challengeDeadline) return;
    setBusy(true);
    onError(null);
    try {
      await api.createGroupChallenge(selectedId, {
        title: challengeTitle,
        description: challengeDescription || null,
        target: Number(challengeTarget),
        reward_xp: Number(challengeReward),
        ends_at: new Date(`${challengeDeadline}T23:59:59`).toISOString()
      });
      setChallengeTitle("");
      setChallengeDescription("");
      setChallengeTarget("3");
      setChallengeReward("75");
      setChallengeDeadline("");
      await refreshTasks(selectedId);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to create team challenge");
    } finally {
      setBusy(false);
    }
  }

  async function removeChallenge(challengeId: string) {
    setBusy(true);
    onError(null);
    try {
      await api.deleteGroupChallenge(challengeId);
      await refreshTasks();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to delete team challenge");
    } finally {
      setBusy(false);
    }
  }

  async function refreshActivity(groupId = selectedId) {
    if (!groupId) return;
    setActivity(await api.groupActivity(groupId));
  }

  async function submitUpdate(event: FormEvent) {
    event.preventDefault();
    if (!selectedId || !updateDraft.trim()) return;
    setBusy(true);
    onError(null);
    try {
      await api.createGroupUpdate(selectedId, updateDraft.trim());
      setUpdateDraft("");
      await refreshActivity(selectedId);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to share group update");
    } finally {
      setBusy(false);
    }
  }

  async function submitActivityComment(event: FormEvent, activityId: string) {
    event.preventDefault();
    const content = commentDrafts[activityId]?.trim();
    if (!content) return;
    setBusy(true);
    onError(null);
    try {
      await api.createGroupActivityComment(activityId, content);
      setCommentDrafts((drafts) => ({ ...drafts, [activityId]: "" }));
      await refreshActivity();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to post comment");
    } finally {
      setBusy(false);
    }
  }

  async function removeActivityComment(commentId: string) {
    setBusy(true);
    onError(null);
    try {
      await api.deleteGroupActivityComment(commentId);
      await refreshActivity();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to delete comment");
    } finally {
      setBusy(false);
    }
  }

  async function toggleRecognition(item: GroupActivity) {
    if (!item.can_react) return;
    onError(null);
    const previousActivity = activity;
    setActivity((items) => items.map((entry) => entry.id === item.id ? {
      ...entry,
      reacted_by_me: !entry.reacted_by_me,
      reactions_count: entry.reactions_count + (entry.reacted_by_me ? -1 : 1)
    } : entry));
    try {
      if (item.reacted_by_me) {
        await api.removeGroupActivityRecognition(item.id);
      } else {
        await api.recognizeGroupActivity(item.id);
      }
      if (selectedId) {
        const nextProgress = await api.groupProgress(selectedId);
        const [nextActivity, nextAchievements] = await Promise.all([
          api.groupActivity(selectedId),
          api.groupAchievements(selectedId)
        ]);
        setActivity(nextActivity);
        setProgress(nextProgress);
        setAchievements(nextAchievements);
      }
    } catch (error) {
      setActivity(previousActivity);
      onError(error instanceof Error ? error.message : "Unable to update recognition");
    }
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
        assigned_to_id: taskAssignee,
        milestone_id: taskMilestone || null
      });
      setTaskTitle("");
      setTaskDescription("");
      setTaskPriority("medium");
      setTaskDeadline("");
      setTaskMilestone("");
      await refreshTasks(selected.id);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to create group task");
    } finally {
      setBusy(false);
    }
  }

  async function changeTask(taskId: string, payload: { status?: TaskStatus; assigned_to_id?: string; milestone_id?: string | null }) {
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

  async function submitMilestone(event: FormEvent) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true);
    onError(null);
    const payload = {
      title: milestoneTitle,
      description: milestoneDescription || null,
      target_date: milestoneDate ? new Date(`${milestoneDate}T23:59:59`).toISOString() : null
    };
    try {
      if (editingMilestoneId) {
        await api.updateGroupMilestone(editingMilestoneId, payload);
      } else {
        await api.createGroupMilestone(selected.id, payload);
      }
      setMilestoneTitle("");
      setMilestoneDescription("");
      setMilestoneDate("");
      setEditingMilestoneId(null);
      await refreshTasks(selected.id);
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to save milestone");
    } finally {
      setBusy(false);
    }
  }

  function editMilestone(milestone: GroupMilestone) {
    setEditingMilestoneId(milestone.id);
    setMilestoneTitle(milestone.title);
    setMilestoneDescription(milestone.description ?? "");
    setMilestoneDate(milestone.target_date?.slice(0, 10) ?? "");
  }

  async function removeMilestone(milestoneId: string) {
    setBusy(true);
    onError(null);
    try {
      await api.deleteGroupMilestone(milestoneId);
      await refreshTasks();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to delete milestone");
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
      if (selectedId) {
        const nextProgress = await api.groupProgress(selectedId);
        const [nextMilestones, nextActivity, nextAnalytics, nextChallenges, nextAchievements] = await Promise.all([
          api.groupMilestones(selectedId),
          api.groupActivity(selectedId),
          api.groupAnalytics(selectedId),
          api.groupChallenges(selectedId),
          api.groupAchievements(selectedId)
        ]);
        setMilestones(nextMilestones);
        setProgress(nextProgress);
        setActivity(nextActivity);
        setAnalytics(nextAnalytics);
        setChallenges(nextChallenges);
        setAchievements(nextAchievements);
      }
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
  const currentGroupMember = progress?.leaderboard.find((entry) => entry.is_current_user);
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
              <button className={selectedId === group.id ? "active" : ""} onClick={() => {
                navigate(`/groups/${group.id}/overview`);
              }} key={group.id}>
                <span className="group-icon"><UsersRound size={17} /></span>
                <span><strong>{group.name}</strong><small>{group.member_count} members</small></span>
                {group.role === "leader" && <Crown size={14} />}
              </button>
            ))}
            {groups.length === 0 && <p className="muted compact-copy">Create a group or join one with a code.</p>}
          </section>

          <section className="group-actions-panel">
            <form className="group-create-form" onSubmit={submitCreate}>
              <h2>Create group</h2>
              <input placeholder="Group name" value={name} onChange={(event) => setName(event.target.value)} required />
              <textarea placeholder="Purpose or shared goal" value={description} onChange={(event) => setDescription(event.target.value)} />
              <button disabled={busy}><Plus size={15} />Create</button>
            </form>
            <div className="group-action-divider"><span>or</span></div>
            <form className="group-join-form" onSubmit={submitJoin}>
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

              <nav className="group-section-nav" aria-label={`${selected.name} workspace sections`}>
                {GROUP_SECTIONS.map(([id, label, Icon]) => (
                  <button
                    className={groupSection === id ? "active" : ""}
                    key={id}
                    onClick={() => navigate(`/groups/${selected.id}/${id}`)}
                  >
                    <Icon size={15} />
                    <span>{label}</span>
                  </button>
                ))}
              </nav>

              {groupSection === "overview" && (
                <>
              {progress && (
                <section className="group-progress">
                  <div className="group-progress-metrics">
                    <div><span className="group-progress-icon xp"><Zap size={17} /></span><span><strong>{progress.total_group_xp}</strong><small>group XP</small></span></div>
                    <div><span className="group-progress-icon done"><CheckCircle2 size={17} /></span><span><strong>{progress.completed_tasks}</strong><small>tasks completed</small></span></div>
                    <div><span className="group-progress-icon streak"><Flame size={17} /></span><span><strong>{progress.team_streak}</strong><small>day team streak</small></span></div>
                  </div>
                  <div className="group-progress-grid">
                    <div className="group-ranking">
                      <div className="section-heading"><h2>Team ranking</h2><span><Trophy size={13} /> Contributions</span></div>
                      <div className="group-ranking-list">
                        {progress.leaderboard.map((entry) => (
                          <article className={entry.is_current_user ? "current" : ""} key={entry.user_id}>
                            <span className="group-rank">{entry.rank === 1 ? <Crown size={15} /> : entry.rank}</span>
                            <span className="avatar">{entry.display_name.slice(0, 1).toUpperCase()}</span>
                            <div><strong>{entry.display_name}</strong><small>{entry.completed_tasks} tasks - {entry.contribution_streak} day streak</small></div>
                            <b>{entry.group_xp} XP</b>
                          </article>
                        ))}
                      </div>
                    </div>
                    <div className="group-rewards">
                      <div className="section-heading"><h2>Recent rewards</h2><span><Award size={13} /> Activity</span></div>
                      <div className="group-reward-list">
                        {progress.recent_rewards.map((reward) => (
                          <article key={reward.id}>
                            <span className="group-reward-icon"><Zap size={14} /></span>
                            <div><strong>{reward.display_name}</strong><small>{reward.reason}</small></div>
                            <b>+{reward.amount}</b>
                          </article>
                        ))}
                        {progress.recent_rewards.length === 0 && <p className="muted compact-copy">Complete a shared task to earn the first reward.</p>}
                      </div>
                    </div>
                  </div>
                </section>
              )}

              <section className="group-achievements">
                <div className="section-heading">
                  <h2>Group achievements</h2>
                  <span><Medal size={13} />{achievements.filter((item) => item.unlocked).length} / {achievements.length} unlocked</span>
                </div>
                <div className="group-achievement-grid">
                  {achievements.map((achievement) => {
                    const percent = Math.min(100, Math.round((achievement.progress / achievement.target) * 100));
                    return (
                      <article className={`${achievement.unlocked ? "unlocked" : ""} ${achievement.rarity}`} key={achievement.code}>
                        <span className="group-achievement-icon">
                          {achievement.unlocked ? groupAchievementIcon(achievement.icon) : <Lock size={18} />}
                        </span>
                        <div>
                          <header>
                            <span>{achievement.rarity}</span>
                            <b>+{achievement.reward_xp} XP each</b>
                          </header>
                          <strong>{achievement.title}</strong>
                          <p>{achievement.description}</p>
                          <div className="group-achievement-progress"><i style={{ width: `${percent}%` }} /></div>
                          <footer>
                            <span>{achievement.progress} / {achievement.target}</span>
                            <time>{achievement.unlocked_at ? `Unlocked ${new Date(achievement.unlocked_at).toLocaleDateString()}` : "In progress"}</time>
                          </footer>
                        </div>
                      </article>
                    );
                  })}
                </div>
              </section>
                </>
              )}

              {groupSection === "challenges" && (
              <section className="group-challenges">
                <div className="section-heading">
                  <h2>Team challenges</h2>
                  <span><Target size={13} />{challenges.filter((item) => item.completed).length} completed</span>
                </div>
                {selected.role === "leader" && (
                  <form className="group-challenge-form" onSubmit={submitChallenge}>
                    <input placeholder="Challenge title" value={challengeTitle} onChange={(event) => setChallengeTitle(event.target.value)} required />
                    <input placeholder="What should the team achieve?" value={challengeDescription} onChange={(event) => setChallengeDescription(event.target.value)} />
                    <label>Tasks<input min="1" max="100" type="number" value={challengeTarget} onChange={(event) => setChallengeTarget(event.target.value)} required /></label>
                    <label>Reward XP<input min="10" max="500" step="5" type="number" value={challengeReward} onChange={(event) => setChallengeReward(event.target.value)} required /></label>
                    <label>Deadline<input type="date" value={challengeDeadline} onChange={(event) => setChallengeDeadline(event.target.value)} required /></label>
                    <button disabled={busy}><Plus size={15} />Start</button>
                  </form>
                )}
                <div className="group-challenge-list">
                  {challenges.map((challenge) => {
                    const percent = Math.min(100, Math.round((challenge.progress / challenge.target) * 100));
                    return (
                      <article className={`${challenge.completed ? "complete" : ""} ${challenge.expired ? "expired" : ""}`} key={challenge.id}>
                        <span className="group-challenge-icon">{challenge.completed ? <Trophy size={18} /> : <Target size={18} />}</span>
                        <div>
                          <header><strong>{challenge.title}</strong><b>+{challenge.reward_xp} XP</b></header>
                          {challenge.description && <p>{challenge.description}</p>}
                          <div className="group-challenge-progress"><i style={{ width: `${percent}%` }} /></div>
                          <footer><span>{challenge.progress} / {challenge.target} completed tasks</span><time>{challenge.completed ? "Complete" : challenge.expired ? "Expired" : `Ends ${new Date(challenge.ends_at).toLocaleDateString()}`}</time></footer>
                        </div>
                        {challenge.can_manage && !challenge.completed && <button title="Delete challenge" onClick={() => removeChallenge(challenge.id)}><Trash2 size={14} /></button>}
                      </article>
                    );
                  })}
                  {challenges.length === 0 && <div className="group-task-empty"><Target size={18} /><span>No team challenge yet</span></div>}
                </div>
              </section>
              )}

              {groupSection === "overview" && analytics && <GroupInsights analytics={analytics} />}

              {groupSection === "members" && selected.role === "leader" && (
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

              {groupSection === "milestones" && (
              <section className="group-milestones">
                <div className="section-heading">
                  <h2>Milestones</h2>
                  <span>{milestones.filter((milestone) => milestone.is_complete).length} / {milestones.length} reached</span>
                </div>
                {selected.role === "leader" && (
                  <form className="milestone-form" onSubmit={submitMilestone}>
                    <input placeholder="Milestone title" value={milestoneTitle} onChange={(event) => setMilestoneTitle(event.target.value)} required />
                    <input placeholder="Outcome or definition of done" value={milestoneDescription} onChange={(event) => setMilestoneDescription(event.target.value)} />
                    <input aria-label="Milestone target date" type="date" value={milestoneDate} onChange={(event) => setMilestoneDate(event.target.value)} />
                    <button disabled={busy}>{editingMilestoneId ? <Save size={15} /> : <Plus size={15} />}{editingMilestoneId ? "Save" : "Add"}</button>
                    {editingMilestoneId && <button className="milestone-cancel" title="Cancel editing" type="button" onClick={() => {
                      setEditingMilestoneId(null);
                      setMilestoneTitle("");
                      setMilestoneDescription("");
                      setMilestoneDate("");
                    }}><X size={15} /></button>}
                  </form>
                )}
                <div className="milestone-list">
                  {milestones.map((milestone) => (
                    <article className={milestone.is_complete ? "complete" : ""} key={milestone.id}>
                      <span className="milestone-icon">{milestone.is_complete ? <CheckCircle2 size={18} /> : <Flag size={18} />}</span>
                      <div className="milestone-copy">
                        <header><strong>{milestone.title}</strong>{milestone.target_date && <time>{new Date(milestone.target_date).toLocaleDateString()}</time>}</header>
                        {milestone.description && <p>{milestone.description}</p>}
                        <div className="milestone-progress"><i style={{ width: `${milestone.progress_percent}%` }} /></div>
                        <small>{milestone.completed_task_count} of {milestone.task_count} linked tasks complete</small>
                      </div>
                      {milestone.can_manage && <div className="milestone-actions">
                        <button title="Edit milestone" onClick={() => editMilestone(milestone)}><Pencil size={14} /></button>
                        <button title="Delete milestone" onClick={() => removeMilestone(milestone.id)}><Trash2 size={14} /></button>
                      </div>}
                    </article>
                  ))}
                  {milestones.length === 0 && <div className="group-task-empty"><Flag size={18} /><span>No milestones</span></div>}
                </div>
              </section>
              )}

              {groupSection === "tasks" && (
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
                    <div>
                      <label>Milestone</label>
                      <select value={taskMilestone} onChange={(event) => setTaskMilestone(event.target.value)}>
                        <option value="">No milestone</option>
                        {milestones.map((milestone) => <option value={milestone.id} key={milestone.id}>{milestone.title}</option>)}
                      </select>
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
                        milestones={milestones}
                        onAssigneeChange={(taskId, assignedToId) => changeTask(taskId, { assigned_to_id: assignedToId })}
                        onDelete={removeTask}
                        onMilestoneChange={(taskId, milestoneId) => changeTask(taskId, { milestone_id: milestoneId || null })}
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
              )}

              {groupSection === "activity" && (
              <section className="group-activity">
                <div className="section-heading">
                  <h2>Team activity</h2>
                  <span><Activity size={13} />{activity.length} updates</span>
                </div>
                <form className="group-update-form" onSubmit={submitUpdate}>
                  <span className="avatar">{currentGroupMember?.display_name.slice(0, 1).toUpperCase() ?? "Y"}</span>
                  <input
                    maxLength={500}
                    placeholder="Share progress, a blocker, or a decision..."
                    value={updateDraft}
                    onChange={(event) => setUpdateDraft(event.target.value)}
                  />
                  <button title="Share update" disabled={busy || !updateDraft.trim()}><Send size={15} /></button>
                </form>
                <div className="group-activity-list">
                  {activity.map((item) => {
                    const discussionOpen = openActivityId === item.id;
                    return (
                      <article className={`group-activity-item ${item.kind}`} key={item.id}>
                        <span className="group-activity-marker">{activityIcon(item.kind)}</span>
                        <div className="group-activity-copy">
                          <header><strong>{item.author.display_name}</strong><time>{relativeGroupTime(item.created_at)}</time></header>
                          <p>{item.content}</p>
                          <div className="group-activity-actions">
                            <button
                              className={item.reacted_by_me ? "recognized" : ""}
                              disabled={!item.can_react}
                              title={item.can_react ? item.reacted_by_me ? "Remove recognition" : "Recognize contribution (+5 group XP)" : "This is your activity"}
                              onClick={() => toggleRecognition(item)}
                            >
                              <Heart size={13} />{item.reactions_count}
                            </button>
                            <button className={discussionOpen ? "active" : ""} onClick={() => setOpenActivityId(discussionOpen ? null : item.id)}>
                              <MessageCircle size={13} />{item.comments.length} {item.comments.length === 1 ? "comment" : "comments"}
                            </button>
                          </div>
                        </div>
                        {discussionOpen && (
                          <div className="group-activity-comments">
                            {item.comments.map((comment) => (
                              <div className="group-activity-comment" key={comment.id}>
                                <span className="avatar">{comment.author.display_name.slice(0, 1).toUpperCase()}</span>
                                <div><strong>{comment.author.display_name}</strong><p>{comment.content}</p><time>{relativeGroupTime(comment.created_at)}</time></div>
                                {comment.can_delete && <button title="Delete comment" onClick={() => removeActivityComment(comment.id)}><Trash2 size={13} /></button>}
                              </div>
                            ))}
                            {item.comments.length === 0 && <p className="muted compact-copy">No comments yet.</p>}
                            <form onSubmit={(event) => submitActivityComment(event, item.id)}>
                              <input
                                maxLength={500}
                                placeholder="Add context or ask a question..."
                                value={commentDrafts[item.id] ?? ""}
                                onChange={(event) => setCommentDrafts((drafts) => ({ ...drafts, [item.id]: event.target.value }))}
                              />
                              <button title="Post comment" disabled={busy || !commentDrafts[item.id]?.trim()}><Send size={14} /></button>
                            </form>
                          </div>
                        )}
                      </article>
                    );
                  })}
                  {activity.length === 0 && <div className="group-task-empty"><Activity size={18} /><span>No group activity yet</span></div>}
                </div>
              </section>
              )}

              {groupSection === "members" && (
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
              )}

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
  milestones: GroupMilestone[];
  onAssigneeChange: (taskId: string, assignedToId: string) => void;
  onDelete: (taskId: string) => void;
  onMilestoneChange: (taskId: string, milestoneId: string) => void;
  onStatusChange: (taskId: string, status: TaskStatus) => void;
  status: TaskStatus;
  tasks: GroupTask[];
};

function GroupTaskColumn({
  icon: Icon,
  label,
  members,
  milestones,
  onAssigneeChange,
  onDelete,
  onMilestoneChange,
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
            milestones={milestones}
            onAssigneeChange={onAssigneeChange}
            onDelete={onDelete}
            onMilestoneChange={onMilestoneChange}
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
  milestones,
  onAssigneeChange,
  onDelete,
  onMilestoneChange,
  onStatusChange,
  task
}: {
  members: ProductivityGroup["members"];
  milestones: GroupMilestone[];
  onAssigneeChange: (taskId: string, assignedToId: string) => void;
  onDelete: (taskId: string) => void;
  onMilestoneChange: (taskId: string, milestoneId: string) => void;
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
        <div className="group-task-admin-fields">
          <select aria-label={`Assignee for ${task.title}`} value={task.assigned_to_id} onChange={(event) => onAssigneeChange(task.id, event.target.value)}>
            {members.map((member) => <option value={member.user_id} key={member.user_id}>{member.display_name || member.email.split("@")[0]}</option>)}
          </select>
          <select aria-label={`Milestone for ${task.title}`} value={task.milestone_id ?? ""} onChange={(event) => onMilestoneChange(task.id, event.target.value)}>
            <option value="">No milestone</option>
            {milestones.map((milestone) => <option value={milestone.id} key={milestone.id}>{milestone.title}</option>)}
          </select>
        </div>
      )}
      {task.milestone_title && <span className="task-milestone"><Flag size={11} />{task.milestone_title}</span>}
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

function activityIcon(kind: GroupActivity["kind"]) {
  if (kind === "achievement_unlocked") return <Medal size={15} />;
  if (kind === "challenge_completed") return <Trophy size={15} />;
  if (kind === "challenge_cancelled") return <X size={15} />;
  if (kind === "challenge_created") return <Target size={15} />;
  if (kind === "task_completed" || kind === "milestone_reached") return <CheckCircle2 size={15} />;
  if (kind.startsWith("milestone")) return <Flag size={15} />;
  if (kind === "member_joined") return <UserPlus size={15} />;
  if (kind.startsWith("task")) return <ClipboardList size={15} />;
  return <MessageCircle size={15} />;
}

function groupAchievementIcon(icon: GroupAchievement["icon"]) {
  if (icon === "check") return <CheckCircle2 size={19} />;
  if (icon === "flag") return <Flag size={19} />;
  if (icon === "trophy") return <Trophy size={19} />;
  if (icon === "heart") return <Heart size={19} />;
  return <Flame size={19} />;
}

function relativeGroupTime(value: string) {
  const seconds = Math.max(0, Math.floor((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  if (seconds < 604800) return `${Math.floor(seconds / 86400)}d ago`;
  return new Date(value).toLocaleDateString();
}

function GroupInsights({ analytics }: { analytics: GroupAnalytics }) {
  const velocityMax = Math.max(1, ...analytics.velocity.map((point) => point.completed));
  const workloadMax = Math.max(1, ...analytics.workload.map((entry) => entry.active_tasks));
  return (
    <section className="group-insights">
      <div className="section-heading">
        <h2>Delivery insights</h2>
        <span><BarChart3 size={13} />Last 14 days</span>
      </div>
      <div className="group-insight-metrics">
        <div><span><Gauge size={15} /></span><strong>{analytics.completion_rate}%</strong><small>completion</small></div>
        <div className={analytics.overdue_tasks ? "warning" : ""}><span><AlertTriangle size={15} /></span><strong>{analytics.overdue_tasks}</strong><small>overdue</small></div>
        <div><span><Clock3 size={15} /></span><strong>{analytics.average_cycle_days}d</strong><small>average cycle</small></div>
        <div><span><UsersRound size={15} /></span><strong>{analytics.workload_balance_score}</strong><small>balance score</small></div>
      </div>
      <div className="group-insight-grid">
        <div className="group-velocity">
          <header><strong>Completion velocity</strong><span>{analytics.due_soon_tasks} due in 7 days</span></header>
          <div className="group-velocity-chart">
            {analytics.velocity.map((point) => (
              <div key={point.date}>
                <i title={`${point.completed} completed`} style={{ height: `${Math.max(4, (point.completed / velocityMax) * 100)}%` }} />
                <time>{new Date(point.date).toLocaleDateString(undefined, { weekday: "narrow" })}</time>
              </div>
            ))}
          </div>
        </div>
        <div className="group-workload">
          <header><strong>Active workload</strong><span>{analytics.active_tasks} open tasks</span></header>
          {analytics.workload.map((entry) => (
            <div className="group-workload-row" key={entry.user_id}>
              <span>{entry.display_name}</span>
              <div><i style={{ width: `${(entry.active_tasks / workloadMax) * 100}%` }} /></div>
              <b>{entry.active_tasks}</b>
              {entry.overdue_tasks > 0 && <small>{entry.overdue_tasks} late</small>}
            </div>
          ))}
        </div>
      </div>
      <div className="group-risk-list">
        <header><strong>Milestone health</strong><span>{analytics.milestone_risks.length} tracked</span></header>
        {analytics.milestone_risks.map((item) => (
          <article key={item.milestone_id}>
            <div><strong>{item.title}</strong><small>{item.progress_percent}% complete{item.target_date ? ` - ${new Date(item.target_date).toLocaleDateString()}` : ""}</small></div>
            <span className={`risk-label ${item.risk}`}>{item.risk.replace("_", " ")}</span>
          </article>
        ))}
        {analytics.milestone_risks.length === 0 && <p className="muted compact-copy">Add milestones to start delivery risk tracking.</p>}
      </div>
    </section>
  );
}
