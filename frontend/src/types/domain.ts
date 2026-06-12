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
  code: string | null;
  title: string;
  description: string;
  category: string;
  rarity: string;
  icon: string;
  awarded_at: string;
  task_id: string | null;
};

export type BadgeProgress = {
  code: string;
  title: string;
  description: string;
  category: string;
  rarity: "common" | "rare" | "epic" | "legendary";
  icon: string;
  progress: number;
  target: number;
  unlocked: boolean;
  awarded_at: string | null;
};

export type Quest = {
  code: string;
  title: string;
  description: string;
  cadence: "daily" | "weekly";
  progress: number;
  target: number;
  reward_xp: number;
  completed: boolean;
  expires_at: string;
};

export type GamificationDashboard = {
  progression: Gamification;
  badges: BadgeProgress[];
  quests: Quest[];
  showcased_badges: BadgeProgress[];
  challenges: Challenge[];
};

export type Challenge = {
  id: string;
  code: string;
  title: string;
  description: string;
  target: number;
  reward_xp: number;
  starts_at: string;
  ends_at: string;
  team_progress: number;
  my_progress: number;
  participant_count: number;
  joined: boolean;
  completed: boolean;
  rewarded: boolean;
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
  current_streak: number;
  last_active_at: string | null;
  is_following: boolean;
};

export type LeaderboardEntry = {
  rank: number;
  user_id: string;
  display_name: string | null;
  email: string;
  avatar_url: string | null;
  level: number;
  current_streak: number;
  weekly_xp: number;
  is_current_user: boolean;
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
  comments_count: number;
};

export type PostComment = {
  id: string;
  content: string;
  created_at: string;
  author: FeedPost["author"];
  can_delete: boolean;
};

export type SocialNotification = {
  id: string;
  kind: "follow" | "reaction" | "comment" | "challenge";
  message: string;
  is_read: boolean;
  created_at: string;
  post_id: string | null;
  actor: FeedPost["author"];
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
