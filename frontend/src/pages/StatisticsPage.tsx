import { FormEvent, useEffect, useState } from "react";

import { api } from "../api/client";
import type { AnalyticsInterval, AnalyticsReport, Stats, TrendPoint } from "../types/domain";

export function StatisticsPage({ stats }: { stats: Stats | null }) {
  const today = toInputDate(new Date());
  const initialFrom = new Date();
  initialFrom.setDate(initialFrom.getDate() - 29);
  const [dateFrom, setDateFrom] = useState(toInputDate(initialFrom));
  const [dateTo, setDateTo] = useState(today);
  const [interval, setInterval] = useState<AnalyticsInterval>("day");
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const statusEntries = Object.entries(stats?.by_status ?? {});

  async function loadAnalytics() {
    setLoading(true);
    setError(null);
    try {
      setReport(await api.analytics(dateFrom, dateTo, interval));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load analytics");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadAnalytics();
  }, []);

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    void loadAnalytics();
  }

  return (
    <section>
      <header className="page-header">
        <div>
          <h1>Statistics</h1>
          <p>Understand completion patterns, workload, and consistency.</p>
        </div>
        <span className="header-stat"><strong>{stats?.completion_rate ?? 0}%</strong> completion</span>
      </header>
      <form className="analytics-filters" onSubmit={applyFilters}>
        <label>
          From
          <input type="date" value={dateFrom} max={dateTo} onChange={(event) => setDateFrom(event.target.value)} />
        </label>
        <label>
          To
          <input type="date" value={dateTo} min={dateFrom} max={today} onChange={(event) => setDateTo(event.target.value)} />
        </label>
        <label>
          Interval
          <select value={interval} onChange={(event) => setInterval(event.target.value as AnalyticsInterval)}>
            <option value="day">Daily</option>
            <option value="week">Weekly</option>
            <option value="month">Monthly</option>
          </select>
        </label>
        <button disabled={loading}>{loading ? "Loading..." : "Apply"}</button>
      </form>
      {error && <div className="alert">{error}</div>}
      <div className="metrics-grid analytics-metrics">
        <Metric label="Created" value={report?.created_tasks ?? 0} />
        <Metric label="Completed" value={report?.completed_tasks ?? 0} />
        <Metric label="Deleted" value={report?.deleted_tasks ?? 0} />
        <Metric label="On time" value={report?.on_time_completed ?? 0} />
        <Metric label="Overdue" value={report?.overdue_completed ?? 0} />
        <Metric label="No deadline" value={report?.without_deadline_completed ?? 0} />
      </div>
      <section className="panel analytics-trend-panel">
        <h2>Activity trend</h2>
        <div className="chart-legend">
          <span><i className="created" />Created</span>
          <span><i className="completed" />Completed</span>
          <span><i className="deleted" />Deleted</span>
        </div>
        <TrendChart points={report?.trend ?? []} />
      </section>
      <div className="two-column">
        <Chart title="By status" entries={statusEntries} />
        <Chart title="Completed by priority" entries={Object.entries(report?.by_priority ?? {})} />
        <Chart title="Completed by category" entries={Object.entries(report?.by_category ?? {})} />
      </div>
    </section>
  );
}

function toInputDate(value: Date) {
  const localDate = new Date(value.getTime() - value.getTimezoneOffset() * 60_000);
  return localDate.toISOString().slice(0, 10);
}

function Metric({ label, value }: { label: string; value: number }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong></div>;
}

function TrendChart({ points }: { points: TrendPoint[] }) {
  const max = Math.max(1, ...points.flatMap((point) => [point.created, point.completed, point.deleted]));
  if (points.length === 0) return <p className="muted">No activity in this period.</p>;

  return (
    <div className="trend-chart">
      {points.map((point) => (
        <div className="trend-period" key={point.period}>
          <div className="trend-bars">
            <i className="created" title={`Created: ${point.created}`} style={{ height: `${(point.created / max) * 100}%` }} />
            <i className="completed" title={`Completed: ${point.completed}`} style={{ height: `${(point.completed / max) * 100}%` }} />
            <i className="deleted" title={`Deleted: ${point.deleted}`} style={{ height: `${(point.deleted / max) * 100}%` }} />
          </div>
          <time>{new Date(`${point.period}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</time>
        </div>
      ))}
    </div>
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
