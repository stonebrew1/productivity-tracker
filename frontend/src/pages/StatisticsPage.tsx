import type { Stats } from "../types/domain";

export function StatisticsPage({ stats }: { stats: Stats | null }) {
  const statusEntries = Object.entries(stats?.by_status ?? {});
  const priorityEntries = Object.entries(stats?.by_priority ?? {});

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Statistics</h1>
          <p>Productivity breakdown by status and priority.</p>
        </div>
      </header>
      <div className="two-column">
        <Chart title="By status" entries={statusEntries} />
        <Chart title="By priority" entries={priorityEntries} />
      </div>
    </section>
  );
}

function Chart({ title, entries }: { title: string; entries: [string, number][] }) {
  const max = Math.max(1, ...entries.map(([, value]) => value));
  return (
    <section className="panel">
      <h2>{title}</h2>
      {entries.length === 0 && <p className="muted">No data yet.</p>}
      {entries.map(([label, value]) => (
        <div className="bar-row" key={label}>
          <span>{label.replace("_", " ")}</span>
          <div><i style={{ width: `${(value / max) * 100}%` }} /></div>
          <strong>{value}</strong>
        </div>
      ))}
    </section>
  );
}
