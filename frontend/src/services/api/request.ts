import { ApiError, type ApiFieldErrors } from "./errors";

export const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

export type RequestOptions = RequestInit & {
  json?: unknown;
  timeoutMs?: number;
};

type ErrorPayload = {
  detail?: unknown;
  message?: unknown;
  errors?: ApiFieldErrors;
};

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers);
  let body = options.body;

  if (options.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(options.json);
  }

  const controller = options.signal ? null : new AbortController();
  let timeoutId: number | undefined;
  if (controller && options.timeoutMs) {
    timeoutId = window.setTimeout(() => controller.abort(), options.timeoutMs);
  }

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
      body,
      signal: options.signal ?? controller?.signal
    });
  } catch {
    throw new ApiError({
      message: `Cannot reach the backend API at ${API_URL}. Make sure the FastAPI server is running on port 8000, then try again.`,
      retryable: true
    });
  } finally {
    if (timeoutId !== undefined) window.clearTimeout(timeoutId);
  }

  if (!response.ok) {
    throw await parseApiError(response);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

async function parseApiError(response: Response): Promise<ApiError> {
  let message = `Request failed with status ${response.status}`;
  let fieldErrors: ApiFieldErrors | null = null;
  try {
    const payload = (await response.json()) as ErrorPayload;
    const detail = payload.detail ?? payload.message;
    fieldErrors = payload.errors ?? null;
    if (typeof detail === "string") {
      message = detail;
    } else if (Array.isArray(detail)) {
      message = detail.map(formatValidationDetail).join("; ");
    } else if (detail && typeof detail === "object" && "message" in detail && typeof detail.message === "string") {
      message = detail.message;
    } else if (detail !== undefined && detail !== null) {
      message = JSON.stringify(detail);
    }
  } catch {
    const text = await response.text();
    if (text) message = text;
  }

  return new ApiError({
    status: response.status,
    message,
    fieldErrors,
    retryable: response.status === 408 || response.status === 429 || response.status >= 500
  });
}

function formatValidationDetail(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && "msg" in value) {
    const maybeDetail = value as { msg?: unknown; loc?: unknown };
    const loc = Array.isArray(maybeDetail.loc) ? `${maybeDetail.loc.join(".")}: ` : "";
    return `${loc}${String(maybeDetail.msg ?? "Validation error")}`;
  }
  return JSON.stringify(value);
}
