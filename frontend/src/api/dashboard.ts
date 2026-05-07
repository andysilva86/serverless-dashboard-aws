import { apiFetch } from "./client";

export type DashboardEvent = {
  PK: string;
  SK: string;
  eventType: string;
  payload: Record<string, unknown>;
  createdAt: string;
};

export type DashboardStats = {
  totalEvents: number;
  byType: Record<string, number>;
  latestEvent: DashboardEvent | null;
};

export type Me = {
  sub: string;
  email: string;
  name: string;
  createdAt: string;
};

export function getStats(token: string): Promise<DashboardStats> {
  return apiFetch<DashboardStats>("/dashboard/stats", { token });
}

export function getMe(token: string): Promise<Me> {
  return apiFetch<Me>("/users/me", { token });
}
