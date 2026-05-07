import { apiFetch } from "./client";

export type LoginResponse = {
  idToken: string;
  accessToken: string;
  refreshToken?: string;
  expiresIn?: number;
  tokenType?: string;
};

export type RegisterResponse = {
  sub: string;
  email: string;
  name: string;
  confirmed: boolean;
};

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiFetch<LoginResponse>("/auth/login", {
    method: "POST",
    body: { email, password },
  });
}

export function register(
  email: string,
  password: string,
  name: string,
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>("/auth/register", {
    method: "POST",
    body: { email, password, name },
  });
}
