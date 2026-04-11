import type {
  ComparisonSettings,
  EvaluationReport,
  LockedFrameworkArtifact,
  RFQDraft,
  RubricProposal,
  SessionSnapshot,
  ValidationIssue,
  VendorPack,
  VendorReview,
} from "./types";

function resolveApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_BASE_URL) {
    return process.env.NEXT_PUBLIC_API_BASE_URL;
  }

  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000`;
  }

  return "http://localhost:8000";
}

const API_BASE_URL = resolveApiBaseUrl();

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
  getVendorPack(sessionId: string): Promise<VendorPack>;
  downloadVendorPack(sessionId: string): Promise<ArtifactDownload>;
  createVendor(sessionId: string, name: string): Promise<SessionSnapshot>;
  updateVendor(sessionId: string, vendorId: string, name: string): Promise<SessionSnapshot>;
  deleteVendor(sessionId: string, vendorId: string): Promise<SessionSnapshot>;
  uploadVendorDocument(sessionId: string, vendorId: string, file: File): Promise<SessionSnapshot>;
  extractVendor(sessionId: string, vendorId: string): Promise<SessionSnapshot>;
  getVendorReview(sessionId: string, vendorId: string): Promise<VendorReview>;
  saveComparisonSettings(sessionId: string, comparisonSettings: ComparisonSettings): Promise<SessionSnapshot>;
  runEvaluation(sessionId: string): Promise<EvaluationReport>;
  getResults(sessionId: string): Promise<EvaluationReport>;
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
  const headers = new Headers(init.headers ?? {});
  if (!(typeof FormData !== "undefined" && init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
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
  getVendorPack(sessionId) {
    return requestJson<VendorPack>(`/sessions/${sessionId}/vendor-pack`, {
      method: "GET",
    });
  },
  async downloadVendorPack(sessionId) {
    const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}/vendor-pack/export`, {
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
  createVendor(sessionId, name) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/vendors`, {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  },
  updateVendor(sessionId, vendorId, name) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/vendors/${vendorId}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    });
  },
  deleteVendor(sessionId, vendorId) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/vendors/${vendorId}`, {
      method: "DELETE",
    });
  },
  uploadVendorDocument(sessionId, vendorId, file) {
    const formData = new FormData();
    formData.append("file", file);
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/vendors/${vendorId}/document`, {
      method: "PUT",
      body: formData,
    });
  },
  extractVendor(sessionId, vendorId) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/vendors/${vendorId}/extract`, {
      method: "POST",
    });
  },
  getVendorReview(sessionId, vendorId) {
    return requestJson<VendorReview>(`/sessions/${sessionId}/vendors/${vendorId}/review`, {
      method: "GET",
    });
  },
  saveComparisonSettings(sessionId, comparisonSettings) {
    return requestJson<SessionSnapshot>(`/sessions/${sessionId}/comparison-settings`, {
      method: "PUT",
      body: JSON.stringify(comparisonSettings),
    });
  },
  runEvaluation(sessionId) {
    return requestJson<EvaluationReport>(`/sessions/${sessionId}/evaluation/run`, {
      method: "POST",
    });
  },
  getResults(sessionId) {
    return requestJson<EvaluationReport>(`/sessions/${sessionId}/results`, {
      method: "GET",
    });
  },
};
