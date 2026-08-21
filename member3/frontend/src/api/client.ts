/**
 * Typed fetch client. One function per endpoint, no wrapper library.
 * Requests go to relative `/api` so the Vite proxy handles dev and the
 * FastAPI static mount handles production from the same origin.
 */

import type {
  EnrichResult,
  ExportStatus,
  Health,
  Job,
  Metrics,
  ResultsPage,
  ReviewAction,
  ReviewRow,
  ReviewState,
  RowDetail,
  RowStatus,
  UploadResult,
} from '../types';

/** Server error envelope: {error: {code, message, row_id, details}}. */
interface ErrorEnvelope {
  error?: { code?: string; message?: string; details?: string[] };
  detail?: unknown;
}

export class ApiError extends Error {
  readonly code: string;
  readonly details: string[];
  readonly status: number;

  constructor(status: number, code: string, message: string, details: string[]) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  if (!response.ok) throw await toApiError(response);
  return (await response.json()) as T;
}

async function toApiError(response: Response): Promise<ApiError> {
  let code = `HTTP_${response.status}`;
  let message = response.statusText || 'Request failed';
  let details: string[] = [];
  try {
    const body = (await response.json()) as ErrorEnvelope;
    if (body.error) {
      code = body.error.code ?? code;
      message = body.error.message ?? message;
      details = body.error.details ?? [];
    } else if (typeof body.detail === 'string') {
      message = body.detail;
    } else if (body.detail && typeof body.detail === 'object') {
      const detail = body.detail as { code?: string; errors?: string[] };
      code = detail.code ?? code;
      details = detail.errors ?? [];
      message = details[0] ?? message;
    }
  } catch {
    // Non-JSON body (e.g. a proxy error page): keep the status-derived message.
  }
  return new ApiError(response.status, code, message, details);
}

export const getHealth = () => request<Health>('/health');

export function uploadFile(file: File): Promise<UploadResult> {
  const body = new FormData();
  body.append('file', file);
  return request<UploadResult>('/upload', { method: 'POST', body });
}

export const loadSample = () => request<UploadResult>('/demo/sample', { method: 'POST' });

export const startEnrichment = (jobId: string, mode = 'full') =>
  request<EnrichResult>('/enrich', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: jobId, mode }),
  });

export const getJob = (jobId: string) => request<Job>(`/jobs/${jobId}`);

export function getResults(
  jobId: string,
  options: { page?: number; pageSize?: number; status?: RowStatus | 'all'; search?: string } = {},
): Promise<ResultsPage> {
  const query = new URLSearchParams({
    page: String(options.page ?? 1),
    page_size: String(options.pageSize ?? 25),
    status: options.status ?? 'all',
    search: options.search ?? '',
  });
  return request<ResultsPage>(`/jobs/${jobId}/results?${query}`);
}

export const getRow = (jobId: string, rowId: number) =>
  request<RowDetail>(`/jobs/${jobId}/results/${rowId}`);

export const getMetrics = (jobId: string) => request<Metrics>(`/jobs/${jobId}/metrics`);

export const getReviewQueue = (jobId: string) =>
  request<{ rows: ReviewRow[] }>(`/jobs/${jobId}/review`);

export const submitReview = (jobId: string, rowId: number, action: ReviewAction, comment = '') =>
  request<{ row_id: number; review: ReviewState }>(`/jobs/${jobId}/review/${rowId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action, comment }),
  });

export const getExportStatus = (jobId: string) =>
  request<ExportStatus>(`/jobs/${jobId}/export/status`);

/**
 * Downloads through a blob so a 409 surfaces as an ApiError instead of
 * navigating the tab to a JSON error page.
 */
export async function downloadExport(jobId: string, format: 'csv' | 'xlsx'): Promise<void> {
  const response = await fetch(`/api/jobs/${jobId}/export.${format}`);
  if (!response.ok) throw await toApiError(response);

  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `fuma_delivery_${jobId}.${format}`;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
