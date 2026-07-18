export type ApiFieldErrors = Record<string, string[] | string>;

export class ApiError extends Error {
  status: number | null;
  fieldErrors: ApiFieldErrors | null;
  retryable: boolean;

  constructor({
    message,
    status = null,
    fieldErrors = null,
    retryable = false
  }: {
    message: string;
    status?: number | null;
    fieldErrors?: ApiFieldErrors | null;
    retryable?: boolean;
  }) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.fieldErrors = fieldErrors;
    this.retryable = retryable;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

export function errorMessage(error: unknown, fallback = "Something went wrong"): string {
  return error instanceof Error ? error.message : fallback;
}

