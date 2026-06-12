import type {
  Achievement,
  AccountabilityCommitment,
  AnalyticsInterval,
  AnalyticsReport,
  Category,
  Challenge,
  FeedPost,
  GamificationDashboard,
  GroupInvitation,
  GroupMilestone,
  GroupTask,
  LeaderboardEntry,
  Person,
  PostComment,
  Profile,
  ProductivityGroup,
  SocialNotification,
  Stats,
  Task,
  TokenResponse,
  User
} from "../types/domain";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";
const ACCESS_TOKEN_KEY = "productivity_access_token";
const REFRESH_TOKEN_KEY = "productivity_refresh_token";

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setTokens(tokens: TokenResponse) {
  localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail ?? "Request failed");
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/auth/me"),
  categories: () => request<Category[]>("/categories"),
  createCategory: (name: string) =>
    request<Category>("/categories", { method: "POST", body: JSON.stringify({ name }) }),
  tasks: () => request<Task[]>("/tasks"),
  createTask: (payload: {
    title: string;
    description?: string;
    priority: string;
    deadline?: string | null;
    scheduled_for?: string | null;
    estimated_minutes?: number | null;
    is_focus?: boolean;
    visibility?: "private" | "public";
    category_id?: string | null;
    parent_id?: string | null;
  }) => request<Task>("/tasks", { method: "POST", body: JSON.stringify(payload) }),
  updateTask: (id: string, payload: Partial<Task>) =>
    request<Task>(`/tasks/${id}`, { method: "PUT", body: JSON.stringify(payload) }),
  completeTask: (id: string) =>
    request<{ task: Task; achievements: Achievement[]; xp_awarded: number }>(`/tasks/${id}/complete`, { method: "POST" }),
  deleteTask: (id: string) => request<void>(`/tasks/${id}`, { method: "DELETE" }),
  achievements: () => request<Achievement[]>("/achievements"),
  gamification: () => request<GamificationDashboard>("/gamification"),
  statistics: () => request<Stats>("/statistics"),
  profile: () => request<Profile>("/social/profile"),
  updateProfile: (payload: { display_name?: string | null; bio?: string | null; avatar_url?: string | null }) =>
    request<Profile>("/social/profile", { method: "PUT", body: JSON.stringify(payload) }),
  people: () => request<Person[]>("/social/people"),
  leaderboard: () => request<LeaderboardEntry[]>("/social/leaderboard"),
  challenges: () => request<Challenge[]>("/social/challenges"),
  joinChallenge: (id: string) => request<Challenge>(`/social/challenges/${id}/join`, { method: "POST" }),
  leaveChallenge: (id: string) => request<void>(`/social/challenges/${id}/join`, { method: "DELETE" }),
  follow: (id: string) => request<void>(`/social/people/${id}/follow`, { method: "POST" }),
  unfollow: (id: string) => request<void>(`/social/people/${id}/follow`, { method: "DELETE" }),
  feed: () => request<FeedPost[]>("/social/feed"),
  comments: (postId: string) => request<PostComment[]>(`/social/posts/${postId}/comments`),
  createComment: (postId: string, content: string) =>
    request<PostComment>(`/social/posts/${postId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content })
    }),
  deleteComment: (id: string) => request<void>(`/social/comments/${id}`, { method: "DELETE" }),
  react: (id: string) => request<void>(`/social/posts/${id}/reaction`, { method: "POST" }),
  unreact: (id: string) => request<void>(`/social/posts/${id}/reaction`, { method: "DELETE" }),
  notifications: () => request<SocialNotification[]>("/social/notifications"),
  markNotificationsRead: () => request<void>("/social/notifications/read", { method: "POST" }),
  commitments: () => request<AccountabilityCommitment[]>("/social/commitments"),
  inviteAccountability: (taskId: string, partnerId: string) =>
    request<AccountabilityCommitment>(`/social/tasks/${taskId}/accountability`, {
      method: "POST",
      body: JSON.stringify({ partner_id: partnerId })
    }),
  acceptCommitment: (id: string) =>
    request<AccountabilityCommitment>(`/social/commitments/${id}/accept`, { method: "POST" }),
  declineCommitment: (id: string) =>
    request<AccountabilityCommitment>(`/social/commitments/${id}/decline`, { method: "POST" }),
  cancelCommitment: (id: string) => request<void>(`/social/commitments/${id}`, { method: "DELETE" }),
  groups: () => request<ProductivityGroup[]>("/groups"),
  createGroup: (payload: { name: string; description?: string | null }) =>
    request<ProductivityGroup>("/groups", { method: "POST", body: JSON.stringify(payload) }),
  joinGroup: (inviteCode: string) =>
    request<ProductivityGroup>("/groups/join", {
      method: "POST",
      body: JSON.stringify({ invite_code: inviteCode })
    }),
  groupInvitations: () => request<GroupInvitation[]>("/groups/invitations"),
  inviteGroupMember: (groupId: string, userId: string) =>
    request<void>(`/groups/${groupId}/invitations`, {
      method: "POST",
      body: JSON.stringify({ user_id: userId })
    }),
  acceptGroupInvitation: (id: string) =>
    request<void>(`/groups/invitations/${id}/accept`, { method: "POST" }),
  declineGroupInvitation: (id: string) =>
    request<void>(`/groups/invitations/${id}/decline`, { method: "POST" }),
  rotateGroupCode: (id: string) =>
    request<ProductivityGroup>(`/groups/${id}/invite-code`, { method: "POST" }),
  groupTasks: (groupId: string) => request<GroupTask[]>(`/groups/${groupId}/tasks`),
  createGroupTask: (groupId: string, payload: {
    title: string;
    description?: string | null;
    priority: "low" | "medium" | "high";
    deadline?: string | null;
    assigned_to_id: string;
    milestone_id?: string | null;
  }) => request<GroupTask>(`/groups/${groupId}/tasks`, {
    method: "POST",
    body: JSON.stringify(payload)
  }),
  updateGroupTask: (taskId: string, payload: Partial<Pick<GroupTask, "title" | "description" | "priority" | "status" | "deadline" | "assigned_to_id" | "milestone_id">>) =>
    request<GroupTask>(`/groups/tasks/${taskId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteGroupTask: (taskId: string) =>
    request<void>(`/groups/tasks/${taskId}`, { method: "DELETE" }),
  groupMilestones: (groupId: string) =>
    request<GroupMilestone[]>(`/groups/${groupId}/milestones`),
  createGroupMilestone: (groupId: string, payload: { title: string; description?: string | null; target_date?: string | null }) =>
    request<GroupMilestone>(`/groups/${groupId}/milestones`, {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  updateGroupMilestone: (milestoneId: string, payload: { title?: string; description?: string | null; target_date?: string | null }) =>
    request<GroupMilestone>(`/groups/milestones/${milestoneId}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deleteGroupMilestone: (milestoneId: string) =>
    request<void>(`/groups/milestones/${milestoneId}`, { method: "DELETE" }),
  analytics: (dateFrom: string, dateTo: string, interval: AnalyticsInterval) => {
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
      interval
    });
    return request<AnalyticsReport>(`/statistics/analytics?${params}`);
  }
};
