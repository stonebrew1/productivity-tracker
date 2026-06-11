import type {
  Achievement,
  AnalyticsInterval,
  AnalyticsReport,
  Category,
  FeedPost,
  GamificationDashboard,
  LeaderboardEntry,
  Person,
  Profile,
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
  follow: (id: string) => request<void>(`/social/people/${id}/follow`, { method: "POST" }),
  unfollow: (id: string) => request<void>(`/social/people/${id}/follow`, { method: "DELETE" }),
  feed: () => request<FeedPost[]>("/social/feed"),
  react: (id: string) => request<void>(`/social/posts/${id}/reaction`, { method: "POST" }),
  unreact: (id: string) => request<void>(`/social/posts/${id}/reaction`, { method: "DELETE" }),
  analytics: (dateFrom: string, dateTo: string, interval: AnalyticsInterval) => {
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
      interval
    });
    return request<AnalyticsReport>(`/statistics/analytics?${params}`);
  }
};
