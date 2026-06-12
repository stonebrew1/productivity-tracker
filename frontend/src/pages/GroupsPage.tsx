import { Check, Copy, Crown, KeyRound, Plus, RefreshCw, Shield, UserPlus, UsersRound, X } from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { GroupInvitation, Person, ProductivityGroup } from "../types/domain";

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
