import { Bell, Check, CheckCheck, Inbox, UserCheck, UserX } from "lucide-react";
import { useEffect, useState } from "react";

import { api } from "../api/client";
import { UserAvatar } from "../components/UserAvatar";
import type { SocialNotification } from "../types/domain";

type Props = {
  onError: (message: string | null) => void;
  onUnreadChange: (count: number) => void;
};

export function InboxPage({ onError, onUnreadChange }: Props) {
  const [notifications, setNotifications] = useState<SocialNotification[]>([]);
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const [loading, setLoading] = useState(true);

  async function loadInbox() {
    const nextNotifications = await api.notifications();
    setNotifications(nextNotifications);
    onUnreadChange(nextNotifications.filter((notification) => !notification.is_read).length);
  }

  useEffect(() => {
    loadInbox()
      .catch((error) => onError(error instanceof Error ? error.message : "Unable to load inbox"))
      .finally(() => setLoading(false));
  }, []);

  async function mutate(action: () => Promise<unknown>) {
    onError(null);
    try {
      await action();
      await loadInbox();
    } catch (error) {
      onError(error instanceof Error ? error.message : "Unable to update inbox");
    }
  }

  const unread = notifications.filter((notification) => !notification.is_read).length;
  const visible = filter === "unread"
    ? notifications.filter((notification) => !notification.is_read)
    : notifications;

  return (
    <section className="inbox-page">
      <header className="page-header">
        <div>
          <h1>Inbox</h1>
          <p>Friend requests, encouragement, comments, and team updates.</p>
        </div>
        {unread > 0 && (
          <button className="inbox-mark-read" onClick={() => mutate(() => api.markNotificationsRead())}>
            <CheckCheck size={16} />Mark all read
          </button>
        )}
      </header>

      <div className="inbox-toolbar">
        <div className="segmented-control">
          <button className={filter === "all" ? "active" : ""} onClick={() => setFilter("all")}>All</button>
          <button className={filter === "unread" ? "active" : ""} onClick={() => setFilter("unread")}>
            Unread {unread > 0 && <b>{unread}</b>}
          </button>
        </div>
        <span>{notifications.length} messages</span>
      </div>

      <div className="inbox-list">
        {loading && <p className="muted">Loading inbox...</p>}
        {!loading && visible.map((notification) => (
          <article className={`inbox-row ${notification.is_read ? "" : "unread"}`} key={notification.id}>
            <span className="inbox-icon">{notification.kind === "friend_request" ? <UserCheck size={18} /> : <Bell size={18} />}</span>
            <UserAvatar
              name={notification.actor.display_name || notification.actor.email}
              avatarUrl={notification.actor.avatar_url}
            />
            <div className="inbox-copy">
              <p><strong>{notification.actor.display_name || notification.actor.email.split("@")[0]}</strong> {notification.message}</p>
              <time>{relativeTime(notification.created_at)}</time>
            </div>
            <div className="inbox-actions">
              {notification.kind === "friend_request" && notification.friendship_id && notification.friendship_status === "pending" && (
                <>
                  <button className="accept" title="Accept request" onClick={() => mutate(() => api.acceptFriendRequest(notification.friendship_id!))}><UserCheck size={16} /></button>
                  <button className="decline" title="Decline request" onClick={() => mutate(() => api.declineFriendRequest(notification.friendship_id!))}><UserX size={16} /></button>
                </>
              )}
              {notification.kind === "friend_request" && notification.friendship_status === "accepted" && (
                <span className="request-resolved"><Check size={14} />Friends</span>
              )}
              {!notification.is_read && (
                <button title="Mark read" onClick={() => mutate(() => api.markNotificationRead(notification.id))}><Check size={16} /></button>
              )}
            </div>
          </article>
        ))}
        {!loading && visible.length === 0 && (
          <div className="inbox-empty">
            <Inbox size={28} />
            <strong>{filter === "unread" ? "You are all caught up." : "Your inbox is empty."}</strong>
            <p>New requests and collaboration updates will appear here.</p>
          </div>
        )}
      </div>
    </section>
  );
}

function relativeTime(value: string) {
  const elapsed = Date.now() - new Date(value).getTime();
  const minutes = Math.max(1, Math.floor(elapsed / 60_000));
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}
