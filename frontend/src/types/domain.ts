export type TaskPriority = "low" | "medium" | "high";
export type TaskStatus = "todo" | "in_progress" | "done";

export type User = {
  id: string;
  email: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  created_at: string;
};

export type Category = {
  id: string;
  name: string;
};

export type Task = {
  id: string;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  deadline: string | null;
  scheduled_for: string | null;
  estimated_minutes: number | null;
  is_focus: boolean;
  visibility: "private" | "public";
  completed_at: string | null;
  category_id: string | null;
  parent_id: string | null;
};

export type Achievement = {
  id: string;
  title: string;
  description: string;
  awarded_at: string;
  task_id: string | null;
};

export type Stats = {
  total_tasks: number;
  completed_tasks: number;
  current_streak: number;
  xp_total: number;
  level: number;
  xp_into_level: number;
  xp_for_next_level: number;
  completion_rate: number;
  by_priority: Record<string, number>;
  by_status: Record<string, number>;
};

export type Gamification = {
  xp_total: number;
  level: number;
  xp_into_level: number;
  xp_for_next_level: number;
  current_streak: number;
};

export type Profile = {
  id: string;
  email: string;
  display_name: string | null;
  bio: string | null;
  avatar_url: string | null;
  gamification: Gamification;
};

export type Person = {
  id: string;
  display_name: string | null;
  email: string;
  avatar_url: string | null;
  level: number;
  is_following: boolean;
};

export type FeedPost = {
  id: string;
  task_title: string;
  xp_awarded: number;
  created_at: string;
  author: {
    id: string;
    display_name: string | null;
    email: string;
    avatar_url: string | null;
    level: number;
  };
  reactions_count: number;
  reacted_by_me: boolean;
};

export type AnalyticsInterval = "day" | "week" | "month";

export type TrendPoint = {
  period: string;
  created: number;
  completed: number;
  deleted: number;
};

export type AnalyticsReport = {
  date_from: string;
  date_to: string;
  interval: AnalyticsInterval;
  created_tasks: number;
  completed_tasks: number;
  deleted_tasks: number;
  on_time_completed: number;
  overdue_completed: number;
  without_deadline_completed: number;
  by_priority: Record<string, number>;
  by_category: Record<string, number>;
  trend: TrendPoint[];
};

export type TokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
};
