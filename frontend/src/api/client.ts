const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const BASE_URL = RAW_BASE_URL.replace(/\/$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string, message: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export type FetchOptions = {
  method?: "GET" | "POST";
  body?: unknown;
  token?: string;
  headers?: Record<string, string>;
};

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { method = "GET", body, token, headers = {} } = options;
  const finalHeaders: Record<string, string> = {
    Accept: "application/json",
    ...headers,
  };
  if (body !== undefined) finalHeaders["Content-Type"] = "application/json";
  if (token) finalHeaders["Authorization"] = `Bearer ${token}`;

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const message =
      (data && typeof data === "object" && "message" in data && typeof data.message === "string"
        ? data.message
        : null) ?? response.statusText;
    const code =
      data && typeof data === "object" && "error" in data && typeof data.error === "string"
        ? data.error
        : "request_failed";
    throw new ApiError(response.status, code, message);
  }

  return data as T;
}
