import { Bell, Check, CheckCircle2, Crown, Flame, Heart, Medal, MessageCircle, Send, Sparkles, Trash2, UserMinus, UserPlus, Zap } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { FeedPost, GamificationDashboard, LeaderboardEntry, Person, PostComment, Profile, SocialNotification } from "../types/domain";

type Props = {
  onError: (message: string | null) => void;
};

export function SocialPage({ onError }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [game, setGame] = useState<GamificationDashboard | null>(null);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [notifications, setNotifications] = useState<SocialNotification[]>([]);
  const [openComments, setOpenComments] = useState<string | null>(null);
  const [comments, setComments] = useState<Record<string, PostComment[]>>({});
  const [commentDraft, setCommentDraft] = useState("");
  const [commentsBusy, setCommentsBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  async function loadSocial() {
    const [nextProfile, nextPeople, nextFeed, nextGame, nextLeaderboard, nextNotifications] = await Promise.all([
      api.profile(),
      api.people(),
      api.feed(),
      api.gamification(),
      api.leaderboard(),
      api.notifications()
    ]);
    setProfile(nextProfile);
    setPeople(nextPeople);
    setFeed(nextFeed);
    setGame(nextGame);
    setLeaderboard(nextLeaderboard);
    setNotifications(nextNotifications);
  }

  useEffect(() => {
    loadSocial()
      .catch((error) => onError(error instanceof Error ? error.message : "Unable to load social workspace"))
      .finally(() => setLoading(false));
  }, []);

  async function mutate(action: () => Promise<unknown>) {
    onError(null);
    try {
      await action();
      await loadSocial();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update social workspace");
    }
  }

  async function toggleComments(postId: string) {
    if (openComments === postId) {
      setOpenComments(null);
      return;
    }
    setOpenComments(postId);
    if (!comments[postId]) {
      try {
        const nextComments = await api.comments(postId);
        setComments((value) => ({ ...value, [postId]: nextComments }));
      } catch (error) {
        onError(error instanceof Error ? error.message : "Unable to load comments");
      }
    }
  }

  async function submitComment(event: FormEvent, postId: string) {
    event.preventDefault();
    if (!commentDraft.trim()) return;
    setCommentsBusy(true);
    try {
      await api.createComment(postId, commentDraft.trim());
      setCommentDraft("");
      const [nextComments] = await Promise.all([api.comments(postId), loadSocial()]);
      setComments((value) => ({ ...value, [postId]: nextComments }));
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to post comment");
    } finally {
      setCommentsBusy(false);
    }
  }

  async function removeComment(postId: string, commentId: string) {
    onError(null);
    try {
      await api.deleteComment(commentId);
      setComments((value) => ({
        ...value,
        [postId]: (value[postId] ?? []).filter((comment) => comment.id !== commentId)
      }));
      await loadSocial();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to delete comment");
    }
  }

  if (loading || !profile) return <p className="muted">Loading social workspace...</p>;

  const progress = Math.round((profile.gamification.xp_into_level / profile.gamification.xp_for_next_level) * 100);
  const socialQuests = game?.quests.filter((quest) =>
    ["weekly_encourage_3", "weekly_comment_2"].includes(quest.code)
  ) ?? [];
  const activePeople = people
    .filter((person) => person.is_following && person.last_active_at)
    .sort((left, right) => new Date(right.last_active_at!).getTime() - new Date(left.last_active_at!).getTime())
    .slice(0, 4);

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Social</h1>
          <p>Build momentum with people who can see the work you choose to share.</p>
        </div>
      </header>

      <section className="profile-strip">
        <Avatar name={profile.display_name ?? profile.email} />
        <div className="profile-identity">
          <strong>{profile.display_name || profile.email.split("@")[0]}</strong>
          <span>{profile.bio || "Add a short goal to your profile."}</span>
        </div>
        <div className="level-progress">
          <div><strong>Level {profile.gamification.level}</strong><span>{profile.gamification.xp_total} XP total</span></div>
          <div className="xp-track"><i style={{ width: `${progress}%` }} /></div>
          <small>{profile.gamification.xp_into_level} / {profile.gamification.xp_for_next_level} XP</small>
        </div>
        <div className="streak-stat"><strong>{profile.gamification.current_streak}</strong><span>streak</span></div>
      </section>

      {game && game.showcased_badges.length > 0 && (
        <section className="profile-showcase">
          <span>Badge showcase</span>
          {game.showcased_badges.map((badge) => (
            <div key={badge.code}><Medal size={16} /><strong>{badge.title}</strong></div>
          ))}
        </section>
      )}

      <div className="social-layout">
        <main className="feed-column">
          {socialQuests.map((socialQuest) => (
            <section className={`social-quest ${socialQuest.completed ? "completed" : ""}`} key={socialQuest.code}>
              <span className="social-quest-icon"><Sparkles size={18} /></span>
              <div>
                <small>Weekly social quest</small>
                <strong>{socialQuest.title}</strong>
                <p>{socialQuest.description}</p>
              </div>
              <div className="social-quest-progress">
                <span>{socialQuest.progress} / {socialQuest.target}</span>
                <i><b style={{ width: `${Math.round((socialQuest.progress / socialQuest.target) * 100)}%` }} /></i>
                <small>+{socialQuest.reward_xp} XP</small>
              </div>
            </section>
          ))}
          <div className="section-heading">
            <h2>Activity feed</h2>
            <span>{feed.length} updates</span>
          </div>
          {feed.length === 0 ? (
            <div className="social-empty">
              <CheckCircle2 size={24} />
              <strong>Your feed is ready.</strong>
              <p>Follow someone or complete a public task to create the first update.</p>
            </div>
          ) : feed.map((post) => (
            <article className="feed-post" key={post.id}>
              <Avatar name={post.author.display_name ?? post.author.email} />
              <div className="feed-copy">
                <div>
                  <strong>{post.author.display_name || post.author.email.split("@")[0]}</strong>
                  <span>Level {post.author.level}</span>
                  <time>{relativeTime(post.created_at)}</time>
                </div>
                <p>Completed <b>{post.task_title}</b></p>
                <small>+{post.xp_awarded} XP</small>
              </div>
              <div className="feed-actions">
                <button
                  className={post.reacted_by_me ? "reaction active" : "reaction"}
                  disabled={post.author.id === profile.id}
                  title={post.author.id === profile.id ? "This is your update" : post.reacted_by_me ? "Remove encouragement" : "Encourage"}
                  onClick={() => mutate(() => post.reacted_by_me ? api.unreact(post.id) : api.react(post.id))}
                ><Heart size={16} />{post.reactions_count}</button>
                <button className={openComments === post.id ? "comment-toggle active" : "comment-toggle"} title="Comments" onClick={() => toggleComments(post.id)}>
                  <MessageCircle size={16} />{post.comments_count}
                </button>
              </div>
              {openComments === post.id && (
                <PostComments
                  comments={comments[post.id]}
                  draft={commentDraft}
                  busy={commentsBusy}
                  onDraft={setCommentDraft}
                  onSubmit={(event) => submitComment(event, post.id)}
                  onDelete={(commentId) => removeComment(post.id, commentId)}
                />
              )}
            </article>
          ))}
        </main>

        <aside className="social-aside">
          <Notifications
            notifications={notifications}
            onRead={() => mutate(() => api.markNotificationsRead())}
          />
          <Leaderboard entries={leaderboard} />
          <section className="active-friends">
            <div className="section-heading"><h2>Active connections</h2><span>Recent progress</span></div>
            {activePeople.map((person) => (
              <div className="active-person" key={person.id}>
                <span className="presence-dot" />
                <Avatar name={person.display_name ?? person.email} />
                <div><strong>{person.display_name || person.email.split("@")[0]}</strong><span>{activeLabel(person.last_active_at!)}</span></div>
                <small><Flame size={12} />{person.current_streak}</small>
              </div>
            ))}
            {activePeople.length === 0 && <p className="muted compact-copy">Follow people to see their recent momentum.</p>}
          </section>
          <ProfileEditor profile={profile} onSave={(payload) => mutate(() => api.updateProfile(payload))} />
          <section className="people-section">
            <div className="section-heading">
              <h2>People</h2>
              <span>{people.filter((person) => person.is_following).length} following</span>
            </div>
            {people.map((person) => (
              <div className="person-row" key={person.id}>
                <Avatar name={person.display_name ?? person.email} />
                <div><strong>{person.display_name || person.email.split("@")[0]}</strong><span>Level {person.level}</span></div>
                <button
                  title={person.is_following ? "Unfollow" : "Follow"}
                  className={person.is_following ? "following" : ""}
                  onClick={() => mutate(() => person.is_following ? api.unfollow(person.id) : api.follow(person.id))}
                >
                  {person.is_following ? <UserMinus size={16} /> : <UserPlus size={16} />}
                </button>
              </div>
            ))}
          </section>
        </aside>
      </div>
    </section>
  );
}

function PostComments({
  comments,
  draft,
  busy,
  onDraft,
  onSubmit,
  onDelete
}: {
  comments: PostComment[] | undefined;
  draft: string;
  busy: boolean;
  onDraft: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <section className="post-comments">
      {!comments ? <p className="muted compact-copy">Loading comments...</p> : comments.map((comment) => (
        <div className="comment-row" key={comment.id}>
          <Avatar name={comment.author.display_name ?? comment.author.email} />
          <div><strong>{comment.author.display_name || comment.author.email.split("@")[0]}</strong><p>{comment.content}</p><time>{relativeTime(comment.created_at)}</time></div>
          {comment.can_delete && <button title="Delete comment" onClick={() => onDelete(comment.id)}><Trash2 size={14} /></button>}
        </div>
      ))}
      {comments?.length === 0 && <p className="muted compact-copy">No comments yet. Start the conversation.</p>}
      <form className="comment-form" onSubmit={onSubmit}>
        <input maxLength={280} placeholder="Write a useful encouragement..." value={draft} onChange={(event) => onDraft(event.target.value)} />
        <button title="Post comment" disabled={busy || !draft.trim()}><Send size={15} /></button>
      </form>
    </section>
  );
}

function Notifications({
  notifications,
  onRead
}: {
  notifications: SocialNotification[];
  onRead: () => Promise<void>;
}) {
  const unread = notifications.filter((notification) => !notification.is_read).length;
  return (
    <section className="notifications-panel">
      <div className="section-heading">
        <h2><Bell size={15} /> Notifications {unread > 0 && <b>{unread}</b>}</h2>
        {unread > 0 && <button title="Mark all read" onClick={onRead}><Check size={15} /></button>}
      </div>
      {notifications.slice(0, 5).map((notification) => (
        <div className={`notification-row ${notification.is_read ? "" : "unread"}`} key={notification.id}>
          <Avatar name={notification.actor.display_name ?? notification.actor.email} />
          <p><strong>{notification.actor.display_name || notification.actor.email.split("@")[0]}</strong> {notification.message}<time>{relativeTime(notification.created_at)}</time></p>
        </div>
      ))}
      {notifications.length === 0 && <p className="muted compact-copy">No notifications yet.</p>}
    </section>
  );
}

function Leaderboard({ entries }: { entries: LeaderboardEntry[] }) {
  return (
    <section className="leaderboard">
      <div className="section-heading"><h2>Weekly leaderboard</h2><span>Resets Monday</span></div>
      {entries.map((entry) => (
        <div className={`leaderboard-row ${entry.is_current_user ? "current" : ""}`} key={entry.user_id}>
          <span className="leaderboard-rank">{entry.rank === 1 ? <Crown size={15} /> : entry.rank}</span>
          <Avatar name={entry.display_name ?? entry.email} />
          <div><strong>{entry.display_name || entry.email.split("@")[0]}{entry.is_current_user ? " (you)" : ""}</strong><span>Level {entry.level}</span></div>
          <b><Zap size={12} />{entry.weekly_xp}</b>
        </div>
      ))}
    </section>
  );
}

function ProfileEditor({
  profile,
  onSave
}: {
  profile: Profile;
  onSave: (payload: { display_name: string; bio: string }) => Promise<void>;
}) {
  const [name, setName] = useState(profile.display_name ?? "");
  const [bio, setBio] = useState(profile.bio ?? "");

  async function submit(event: FormEvent) {
    event.preventDefault();
    await onSave({ display_name: name, bio });
  }

  return (
    <form className="profile-editor" onSubmit={submit}>
      <div className="section-heading"><h2>Edit profile</h2></div>
      <label>Display name<input value={name} maxLength={80} onChange={(event) => setName(event.target.value)} /></label>
      <label>Current goal<textarea value={bio} maxLength={500} onChange={(event) => setBio(event.target.value)} /></label>
      <button>Save profile</button>
    </form>
  );
}

function Avatar({ name }: { name: string }) {
  return <span className="avatar" aria-hidden="true">{name.trim().slice(0, 1).toUpperCase()}</span>;
}

function relativeTime(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.floor(elapsed / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function activeLabel(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const hours = Math.max(0, Math.floor(elapsed / 3_600_000));
  if (hours < 1) return "Active this hour";
  if (hours < 24) return `Active ${hours}h ago`;
  return `Active ${Math.floor(hours / 24)}d ago`;
}
