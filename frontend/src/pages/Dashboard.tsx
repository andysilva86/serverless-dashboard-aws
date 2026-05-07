import { useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { getMe, getStats } from "../api/dashboard";
import type { DashboardStats, Me } from "../api/dashboard";
import { ApiError } from "../api/client";

export default function Dashboard() {
  const { session, signOut } = useAuth();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([getMe(session.idToken), getStats(session.idToken)])
      .then(([meResp, statsResp]) => {
        if (cancelled) return;
        setMe(meResp);
        setStats(statsResp);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          signOut();
          return;
        }
        const message = err instanceof Error ? err.message : "Erro ao carregar";
        setError(message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [session, signOut]);

  if (loading) return <p className="muted">Carregando dashboard…</p>;
  if (error) return <p className="error">{error}</p>;
  if (!stats || !me) return null;

  const eventTypes = Object.entries(stats.byType);

  return (
    <>
      <h1 style={{ marginTop: 0 }}>Olá, {me.name || me.email}</h1>
      <p className="muted">Visão geral dos seus eventos sistêmicos.</p>

      <div className="dashboard__grid">
        <div className="metric">
          <div className="metric__label">Eventos totais</div>
          <div className="metric__value">{stats.totalEvents}</div>
        </div>
        <div className="metric">
          <div className="metric__label">Tipos distintos</div>
          <div className="metric__value">{eventTypes.length}</div>
        </div>
        <div className="metric">
          <div className="metric__label">Último evento</div>
          <div className="metric__value" style={{ fontSize: "1rem" }}>
            {stats.latestEvent
              ? new Date(stats.latestEvent.createdAt).toLocaleString()
              : "—"}
          </div>
        </div>
      </div>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Eventos por tipo</h2>
        {eventTypes.length === 0 ? (
          <p className="muted">
            Nenhum evento ainda. Envie um para <code>POST /integrations/webhook</code> ou{" "}
            <code>POST /integrations/dispatch</code>.
          </p>
        ) : (
          <ul className="event-list">
            {eventTypes
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <li key={type}>
                  <span className="tag">{type}</span>
                  <strong>{count}</strong>
                </li>
              ))}
          </ul>
        )}
      </section>
    </>
  );
}
