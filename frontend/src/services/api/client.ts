import { API_URL, request } from "./request";

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, json?: unknown) => request<T>(path, { method: "POST", json }),
  put: <T>(path: string, json?: unknown) => request<T>(path, { method: "PUT", json }),
  patch: <T>(path: string, json?: unknown) => request<T>(path, { method: "PATCH", json }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  upload: <T>(path: string, formData: FormData) => request<T>(path, { method: "POST", body: formData })
};

export const assetFileUrl = (assetId: string) => `${API_URL}/assets/${assetId}/file`;
export const generatedResumePdfUrl = (actorProfileId: string) =>
  `${API_URL}/representation/acting-credits/resume-pdf/${actorProfileId}`;
export const generatedResumeDocxUrl = (actorProfileId: string) =>
  `${API_URL}/representation/acting-credits/resume-docx/${actorProfileId}`;

export { API_URL, request };
export * from "./errors";

