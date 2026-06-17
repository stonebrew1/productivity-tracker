import type { TaskPriority } from "../types/domain";

export function calculateTaskXp(priority: TaskPriority, estimatedMinutes: number | null) {
  const priorityBonus = { low: 0, medium: 5, high: 10 }[priority];
  const minutes = estimatedMinutes ?? 30;
  const effortBonus = minutes <= 15
    ? 0
    : minutes <= 30
      ? 5
      : minutes <= 60
        ? 10
        : minutes <= 120
          ? 20
          : minutes <= 240
            ? 30
            : 40;
  return 10 + priorityBonus + effortBonus;
}
