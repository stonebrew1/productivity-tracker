import { Medal } from "lucide-react";

import type { Achievement } from "../types/domain";

export function AchievementsPage({ achievements }: { achievements: Achievement[] }) {
  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Achievements</h1>
          <p>Milestones awarded from completed work.</p>
        </div>
      </header>
      <div className="achievement-grid">
        {achievements.map((achievement) => (
          <article className="achievement-card" key={achievement.id}>
            <Medal size={22} />
            <h2>{achievement.title}</h2>
            <p>{achievement.description}</p>
            <time>{new Date(achievement.awarded_at).toLocaleString()}</time>
          </article>
        ))}
      </div>
      {achievements.length === 0 && <p className="muted">No achievements yet.</p>}
    </section>
  );
}
