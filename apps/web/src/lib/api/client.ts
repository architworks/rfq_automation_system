import type {
  LockedFrameworkArtifact,
  RFQDraft,
  RubricProposal,
  SessionSnapshot,
  ValidationIssue,
} from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ErrorDetail = string | { detail?: unknown } | ValidationIssue[];

export class ApiError extends Error {
  status: number;
  detail: ErrorDetail;

  constructor(message: string, status: number, detail: ErrorDetail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export interface ArtifactDownload {
  blob: Blob;
  fileName: string;
}

export interface RfqApiClient {
  createOrHydrateSession(sessionId?: string): Promise<SessionSnapshot>;
  getSession(sessionId: string): Promise<SessionSnapshot>;
  saveRfq(sessionId: string, draft: RFQDraft): Promise<SessionSnapshot>;
  generateRubric(sessionId: string): Promise<SessionSnapshot>;
  saveRubric(sessionId: string, proposal: RubricProposal): Promise<SessionSnapshot>;
  lockRubric(sessionId: string): Promise<LockedFrameworkArtifact>;
  downloadArtifact(sessionId: string): Promise<ArtifactDownload>;
}

async function parseError(response: Response): Promise<ApiError> {
  let detail: ErrorDetail = response.statusText;

  try {
    const payload = (await response.json()) as ErrorDetail;
    detail = payload;
  } catch {
    try {
      detail = await response.text();
    } catch {
      detail = response.statusText;
    }
  }

  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? "Request failed with validation issues."
        : typeof detail === "object" && detail && "detail" in detail && typeof detail.detail === "string"
          ? detail.detail
          : "Request failed.";

  return new ApiError(message, response.status, detail);
}

async function requestJson<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await parseError(response);
  }

  return (await response.json()) as T;
}

function extractFileName(contentDisposition: string | null): string {
  if (!contentDisposition) {
    return "locked-framework.json";
  }

  const match = /filename="([^"]+)"/.exec(contentDisposition);
  return match?.[1] ?? "locked-framework.json";
}

export const apiClient: RfqApiClient = {
  createOrHydrateSession(sessionId) {
    return requestJson<SessionSnapshot>("/sessions", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId ?? null }),
    });
  },
  getSession(sessionId) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}`, {
      method: "GET",
    });
  },
  saveRfq(sessionId, draft) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/rfq`, {
      method: "PUT",
      body: JSON.stringify(draft),
    });
  },
  generateRubric(sessionId) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/rubric/generate`, {
      method: "POST",
    });
  },
  saveRubric(sessionId, proposal) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/rubric`, {
      method: "PATCH",
      body: JSON.stringify(proposal),
    });
  },
  lockRubric(sessionId) {
    return requestJson<LockedFrameworkArtifact>(`/sessions/${sessionId}/rubric/lock`, {
      method: "POST",
    });
  },
  async downloadArtifact(sessionId) {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/artifact`, {
      method: "GET",
      cache: "no-store",
    });

    if (!response.ok) {
      throw await parseError(response);
    }

    return {
      blob: await response.blob(),
      fileName: extractFileName(response.headers.get("content-disposition")),
    };
  },
};
