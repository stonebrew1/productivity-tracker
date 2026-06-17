import {
  Check,
  CheckCircle2,
  Clock3,
  Flame,
  Globe2,
  Lock,
  Medal,
  Plus,
  Target,
  Trophy,
  UsersRound,
  Zap
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { Achievement, BadgeProgress, GamificationDashboard, Quest, Task } from "../types/domain";

export function AchievementsPage({ tasks, onChanged, onError }: { tasks: Task[]; onChanged: () => Promise<void>; onError: (message: string | null) => void }) {
  const [dashboard, setDashboard] = useState<GamificationDashboard | null>(null);
  const [achievements, setAchievements] = useState<Achievement[]>([]);
  const [tab, setTab] = useState<"overview" | "quests" | "badges" | "personal">("overview");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [taskId, setTaskId] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api.gamification(), api.achievements()])
      .then(([nextDashboard, nextAchievements]) => {
        setDashboard(nextDashboard);
        setAchievements(nextAchievements);
      })
      .catch((error) => onError(error instanceof Error ? error.message : "Unable to load gamification"));
  }, []);

  async function submitAchievement(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    onError(null);
    try {
      const achievement = await api.createAchievement({ title, description, task_id: taskId });
      setAchievements((current) => [achievement, ...current]);
      setTitle("");
      setDescription("");
      setTaskId("");
      await onChanged();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to add achievement");
    } finally {
      setBusy(false);
    }
  }

  if (!dashboard) return <p className="muted">Loading gamification...</p>;

  const game = dashboard.progression;
  const levelProgress = Math.round((game.xp_into_level / game.xp_for_next_level) * 100);

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Progression</h1>
          <p>Your consistency, quests, and earned milestones.</p>
        </div>
      </header>

      <section className="game-progress">
        <div className="level-mark"><span>Level</span><strong>{game.level}</strong></div>
        <div className="game-progress-copy">
          <div><strong>{game.xp_total} XP</strong><span>{game.xp_into_level} / {game.xp_for_next_level} to next level</span></div>
          <div className="xp-track"><i style={{ width: `${levelProgress}%` }} /></div>
        </div>
        <div className="game-streak"><Flame size={20} /><strong>{game.current_streak}</strong><span>day streak</span></div>
      </section>

      <nav className="page-tabs" aria-label="Progression views">
        {(["overview", "quests", "badges", "personal"] as const).map((item) => <button className={tab === item ? "active" : ""} onClick={() => setTab(item)} key={item}>{item}</button>)}
      </nav>

      {(tab === "overview" || tab === "quests") && <section className="quest-section">
        <div className="section-heading">
          <h2>Active quests</h2>
          <span>{dashboard.quests.filter((quest) => quest.completed).length} completed</span>
        </div>
        <div className="quest-grid">
          {dashboard.quests.map((quest) => <QuestCard quest={quest} key={quest.code} />)}
        </div>
      </section>}

      {tab === "overview" && <section className="progress-challenges">
        <div className="section-heading">
          <h2>Team challenges</h2>
          <span>{dashboard.challenges.filter((challenge) => challenge.completed).length} completed</span>
        </div>
        <div className="challenge-grid">
          {dashboard.challenges.filter((challenge) => challenge.joined).map((challenge) => (
            <article className={`progress-challenge ${challenge.completed ? "completed" : ""}`} key={challenge.id}>
              <header><span><UsersRound size={14} />{challenge.participant_count} participants</span><strong>+{challenge.reward_xp} XP</strong></header>
              <h3>{challenge.title}</h3>
              <p>{challenge.description}</p>
              <div className="quest-progress"><i style={{ width: `${Math.round((challenge.team_progress / challenge.target) * 100)}%` }} /></div>
              <footer><span>{challenge.team_progress} / {challenge.target} team tasks</span><b>{challenge.completed ? "Complete" : `${challenge.my_progress} yours`}</b></footer>
            </article>
          ))}
        </div>
      </section>}

      {(tab === "overview" || tab === "badges") && <section>
        <div className="section-heading badge-heading">
          <h2>Badge collection</h2>
          <span>{dashboard.badges.filter((badge) => badge.unlocked).length} / {dashboard.badges.length} unlocked</span>
        </div>
        <div className="badge-catalog">
          {dashboard.badges.map((badge) => <BadgeCard badge={badge} key={badge.code} />)}
        </div>
      </section>}

      {tab === "personal" && (
        <section className="personal-achievements">
          <section className="panel achievement-composer">
            <div className="section-heading"><h2>Add achievement</h2><span>Link a meaningful result to a task</span></div>
            <form onSubmit={submitAchievement}>
              <input placeholder="Achievement title" value={title} onChange={(event) => setTitle(event.target.value)} required />
              <textarea placeholder="What did you accomplish?" value={description} onChange={(event) => setDescription(event.target.value)} required />
              <select value={taskId} onChange={(event) => setTaskId(event.target.value)} required>
                <option value="">Choose related task</option>
                {tasks.map((task) => <option value={task.id} key={task.id}>{task.title}</option>)}
              </select>
              <button disabled={busy || !taskId}><Plus size={16} />{busy ? "Adding..." : "Add achievement"}</button>
            </form>
          </section>
          <div className="personal-achievement-list">
            {achievements.filter((achievement) => achievement.code === null).map((achievement) => (
              <article className="personal-achievement" key={achievement.id}>
                <span><Medal size={19} /></span>
                <div><h3>{achievement.title}</h3><p>{achievement.description}</p><small>{new Date(achievement.awarded_at).toLocaleDateString()}</small></div>
              </article>
            ))}
            {achievements.every((achievement) => achievement.code !== null) && (
              <div className="empty-state"><Medal size={22} /><strong>No personal achievements yet</strong><p>Record a result and connect it to the task that made it happen.</p></div>
            )}
          </div>
        </section>
      )}
    </section>
  );
}

function QuestCard({ quest }: { quest: Quest }) {
  const progress = Math.round((quest.progress / quest.target) * 100);
  return (
    <article className={`quest-card ${quest.completed ? "completed" : ""}`}>
      <header>
        <span>{quest.cadence}</span>
        <strong>+{quest.reward_xp} XP</strong>
      </header>
      <h3>{quest.title}</h3>
      <p>{quest.description}</p>
      <div className="quest-progress"><i style={{ width: `${progress}%` }} /></div>
      <footer>
        <span>{quest.progress} / {quest.target}</span>
        {quest.completed ? <b><Check size={14} /> Complete</b> : <time>{expiresLabel(quest.expires_at)}</time>}
      </footer>
    </article>
  );
}

function BadgeCard({ badge }: { badge: BadgeProgress }) {
  const Icon = badgeIcon(badge.icon);
  const progress = Math.round((badge.progress / badge.target) * 100);
  return (
    <article className={`badge-card ${badge.unlocked ? "unlocked" : "locked"} ${badge.rarity}`}>
      <div className="badge-symbol">{badge.unlocked ? <Icon size={24} /> : <Lock size={20} />}</div>
      <div className="badge-copy">
        <div><span>{badge.category}</span><b>{badge.rarity}</b></div>
        <h3>{badge.title}</h3>
        <p>{badge.description}</p>
        <div className="badge-progress"><i style={{ width: `${progress}%` }} /></div>
        <small>{badge.unlocked ? `Unlocked ${new Date(badge.awarded_at!).toLocaleDateString()}` : `${badge.progress} / ${badge.target}`}</small>
      </div>
    </article>
  );
}

function badgeIcon(name: string) {
  if (name === "check") return CheckCircle2;
  if (name === "zap") return Zap;
  if (name === "target") return Target;
  if (name === "clock") return Clock3;
  if (name === "globe") return Globe2;
  if (name === "flame") return Flame;
  if (name === "trophy") return Trophy;
  return Medal;
}

function expiresLabel(value: string) {
  const remaining = Math.max(0, new Date(value).getTime() - Date.now());
  const hours = Math.ceil(remaining / 3_600_000);
  if (hours < 24) return `${hours}h left`;
  return `${Math.ceil(hours / 24)}d left`;
}
