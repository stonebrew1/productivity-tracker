import { CheckCircle2, Heart, UserMinus, UserPlus } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { FeedPost, Person, Profile } from "../types/domain";

type Props = {
  onError: (message: string | null) => void;
};

export function SocialPage({ onError }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [people, setPeople] = useState<Person[]>([]);
  const [feed, setFeed] = useState<FeedPost[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadSocial() {
    const [nextProfile, nextPeople, nextFeed] = await Promise.all([
      api.profile(),
      api.people(),
      api.feed()
    ]);
    setProfile(nextProfile);
    setPeople(nextPeople);
    setFeed(nextFeed);
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

  if (loading || !profile) return <p className="muted">Loading social workspace...</p>;

  const progress = Math.round((profile.gamification.xp_into_level / profile.gamification.xp_for_next_level) * 100);

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

      <div className="social-layout">
        <main className="feed-column">
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
              <button
                className={post.reacted_by_me ? "reaction active" : "reaction"}
                title={post.reacted_by_me ? "Remove encouragement" : "Encourage"}
                onClick={() => mutate(() => post.reacted_by_me ? api.unreact(post.id) : api.react(post.id))}
              >
                <Heart size={16} />
                {post.reactions_count}
              </button>
            </article>
          ))}
        </main>

        <aside className="social-aside">
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
