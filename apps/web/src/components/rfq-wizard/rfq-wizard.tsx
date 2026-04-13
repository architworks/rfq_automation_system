"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  apiClient,
  type BuyerPriority,
  type RfqApiClient,
  type Criterion,
  type CriterionType,
  type DeterministicScoringGuide,
  type DeterministicScoringRule,
  type EvaluationReport,
  type EvidenceCheck,
  type LLMSettings,
  type LineItem,
  type LockedFrameworkArtifact,
  type ReasoningEffort,
  type RFQDraft,
  type ResponseSchedule,
  type RubricSection,
  type RubricProposal,
  type ScheduleColumn,
  type SessionSnapshot,
  type ValidationIssue,
  type VendorPack,
} from "@/lib/api";
import { RFQ_UOM_OPTIONS, SUPPORTED_RFQ_CURRENCIES } from "@/lib/normalization-catalog";
import {
  CRITERION_TYPE_OPTIONS,
  cloneValue,
  createBuyerPriority,
  createCriterion,
  createEvidenceCheck,
  createLineItem,
  createResponseSchedule,
  createScheduleColumn,
  createSection,
  parseCsv,
  toCsv,
} from "@/lib/rubric-factories";
import { setStoredSessionId } from "@/lib/session";
import { buildVendorPackDocument } from "@/lib/vendor-pack-docx";
import { FormInput, FormSelect, FormTextarea } from "./form-fields";
import { PackStep, ResultsStep, ReviewStep, VendorsStep } from "./phase-two";

import styles from "./rfq-wizard.module.css";

export type WizardStep = "input" | "proposal" | "lock" | "pack" | "vendors" | "review" | "results";

const DEFAULT_AUTOSAVE_MS = 700;
const REASONING_EFFORT_OPTIONS: Array<{ value: ReasoningEffort; label: string }> = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "xhigh", label: "XHigh" },
];

function parseNumber(value: string): number | null {
  if (!value.trim()) {
    return null;
  }

  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatTimestamp(value?: string): string {
  if (!value) {
    return "Not yet saved";
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function createDefaultLlmSettings(): LLMSettings {
  return {
    reasoning_effort: "high",
  };
}

function normalizeValidationIssues(detail: unknown): ValidationIssue[] {
  if (Array.isArray(detail)) {
    return detail.filter(
      (entry): entry is ValidationIssue =>
        typeof entry === "object" &&
        entry !== null &&
        "field" in entry &&
        "message" in entry,
    );
  }

  if (typeof detail === "object" && detail && "detail" in detail) {
    return normalizeValidationIssues((detail as { detail?: unknown }).detail);
  }

  return [];
}

function blobToDownload(blob: Blob, fileName: string) {
  const url = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.URL.revokeObjectURL(url);
}

function snapshotToJson(value: unknown): string {
  return JSON.stringify(value ?? null);
}

type ScheduleFieldPreview = {
  fieldId: string;
  scheduleId: string;
  scheduleName: string;
  columnId: string;
  columnLabel: string;
  description: string;
  required: boolean;
};

function buildScheduleFieldLookup(responseSchedules: ResponseSchedule[]): Map<string, ScheduleFieldPreview> {
  const entries = responseSchedules.flatMap((schedule) =>
    schedule.columns.map((column) => [
      `${schedule.id}.${column.id}`,
      {
        fieldId: `${schedule.id}.${column.id}`,
        scheduleId: schedule.id,
        scheduleName: schedule.name,
        columnId: column.id,
        columnLabel: column.label,
        description: column.description,
        required: column.required,
      },
    ] as const),
  );

  return new Map(entries);
}

function formatCriterionMode(criterion: Criterion): string {
  switch (criterion.criterion_type) {
    case "mac":
      return "Mandatory gate · pass/fail only";
    case "technical_cutoff_backed":
      return `Scored criterion with minimum qualifying score${criterion.min_cutoff !== null ? ` · cutoff ${criterion.min_cutoff}/${criterion.max_score ?? "?"}` : ""}`;
    case "technical_scored_only":
      return `Scored criterion without individual cutoff${criterion.max_score !== null ? ` · max ${criterion.max_score}` : ""}`;
    case "commercial":
      return "Commercial capture only";
    default:
      return "Criterion";
  }
}

function isTechnicalCriterion(criterion: Criterion): boolean {
  return criterion.criterion_type !== "commercial";
}

function usesQualitativeScoring(criterion: Criterion): boolean {
  return (
    criterion.criterion_type !== "mac" &&
    criterion.criterion_type !== "commercial" &&
    !criterion.deterministic_scoring
  );
}

function formatCriterionTypeLabel(criterionType: CriterionType): string {
  return CRITERION_TYPE_OPTIONS.find((option) => option.value === criterionType)?.label ?? criterionType;
}

function formatCriterionWeight(criterion: Criterion): string {
  if (criterion.criterion_type === "mac") {
    return "Not part of technical scoring";
  }

  if (criterion.criterion_type === "commercial") {
    return "Commercial only";
  }

  return typeof criterion.weight === "number" ? String(criterion.weight) : "Not set";
}

function formatCriterionCutoff(criterion: Criterion): string {
  if (criterion.criterion_type === "mac") {
    return "Pass/Fail only";
  }

  if (criterion.criterion_type === "technical_scored_only") {
    return "None";
  }

  if (criterion.criterion_type === "commercial") {
    return "Not applicable";
  }

  return typeof criterion.min_cutoff === "number" ? String(criterion.min_cutoff) : "Not set";
}

function formatCriterionMaxScore(criterion: Criterion): string {
  if (criterion.criterion_type === "mac") {
    return "Not scored";
  }

  return typeof criterion.max_score === "number" ? String(criterion.max_score) : "Not set";
}

function formatScoringResult(rule: DeterministicScoringRule): string {
  if (typeof rule.score === "number") {
    return String(rule.score);
  }

  if (rule.outcome === "pass") {
    return "Pass";
  }

  if (rule.outcome === "fail") {
    return "Fail";
  }

  return "Review";
}

type RfqWizardProps = {
  sessionId: string;
  step: WizardStep;
  onStepChange: (step: WizardStep) => void;
  onSessionReplace?: (sessionId: string, step: WizardStep) => void;
  api?: RfqApiClient;
  autosaveMs?: number;
};

export function RfqWizard({
  sessionId,
  step,
  onStepChange,
  onSessionReplace,
  api = apiClient,
  autosaveMs = DEFAULT_AUTOSAVE_MS,
}: RfqWizardProps) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [rfqDraft, setRfqDraft] = useState<RFQDraft | null>(null);
  const [rubricProposal, setRubricProposal] = useState<RubricProposal | null>(null);
  const [lockedArtifact, setLockedArtifact] = useState<LockedFrameworkArtifact | null>(null);
  const [evaluationReport, setEvaluationReport] = useState<EvaluationReport | null>(null);
  const [llmSettingsDraft, setLlmSettingsDraft] = useState<LLMSettings>(createDefaultLlmSettings());
  const [selectedVendorId, setSelectedVendorId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLocking, setIsLocking] = useState(false);
  const [isResettingSession, setIsResettingSession] = useState(false);
  const [isApplyingTemplate, setIsApplyingTemplate] = useState(false);
  const [isLoadingGeneratedSampleRubric, setIsLoadingGeneratedSampleRubric] = useState(false);
  const [isSavingLlmSettings, setIsSavingLlmSettings] = useState(false);
  const [isRunningEvaluation, setIsRunningEvaluation] = useState(false);
  const [uploadingVendorId, setUploadingVendorId] = useState<string | null>(null);
  const [isExtractingVendors, setIsExtractingVendors] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [autosaveMessage, setAutosaveMessage] = useState("Waiting for changes");
  const [downloadState, setDownloadState] = useState<"idle" | "ready" | "done" | "error">("idle");
  const [vendorPackDownloadState, setVendorPackDownloadState] = useState<"idle" | "ready" | "done" | "error">("idle");
  const [vendorDocumentDownloadState, setVendorDocumentDownloadState] = useState<"idle" | "ready" | "done" | "error">("idle");
  const [sampleTemplateDraft, setSampleTemplateDraft] = useState<RFQDraft | null>(null);

  const initialisedRef = useRef(false);
  const savedRfqRef = useRef("");
  const savedRubricRef = useRef("");

  function applySessionSnapshot(loaded: SessionSnapshot) {
    const vendors = loaded.vendors ?? [];
    setSnapshot(loaded);
    setLlmSettingsDraft(cloneValue(loaded.llm_settings ?? createDefaultLlmSettings()));
    setLockedArtifact(loaded.locked_artifact ?? null);
    setEvaluationReport(loaded.evaluation_report ?? null);
    setDownloadState(loaded.locked_artifact ? "ready" : "idle");
    setVendorPackDownloadState(loaded.vendor_pack ? "ready" : "idle");
    setVendorDocumentDownloadState(loaded.locked_artifact && loaded.vendor_pack ? "ready" : "idle");
    setSelectedVendorId((current) => {
      if (vendors.length === 0) {
        return null;
      }
      if (current && vendors.some((vendor) => vendor.id === current)) {
        return current;
      }
      return vendors[0].id;
    });
  }

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      setIsLoading(true);
      setRequestError(null);

      try {
        let loaded: SessionSnapshot;
        try {
          loaded = await api.getSession(sessionId);
        } catch (error) {
          if (error instanceof ApiError && error.status === 404) {
            loaded = await api.createOrHydrateSession(sessionId);
          } else {
            throw error;
          }
        }
        if (cancelled) {
          return;
        }

        applySessionSnapshot(loaded);
        setRfqDraft(loaded.rfq_draft);
        setRubricProposal(loaded.rubric_proposal ?? null);
        savedRfqRef.current = snapshotToJson(loaded.rfq_draft);
        savedRubricRef.current = snapshotToJson(loaded.rubric_proposal);
        initialisedRef.current = true;
      } catch (error) {
        if (!cancelled) {
          setRequestError(error instanceof Error ? error.message : "Failed to load session.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void loadSession();

    return () => {
      cancelled = true;
    };
  }, [api, sessionId]);

  useEffect(() => {
    let cancelled = false;

    async function loadSampleTemplateReference() {
      try {
        const sampleTemplate = await api.getRfqTemplate("sample");
        if (!cancelled) {
          setSampleTemplateDraft(sampleTemplate);
        }
      } catch {
        if (!cancelled) {
          setSampleTemplateDraft(null);
        }
      }
    }

    void loadSampleTemplateReference();

    return () => {
      cancelled = true;
    };
  }, [api]);

  const rfqSignature = useMemo(() => snapshotToJson(rfqDraft), [rfqDraft]);
  const rubricSignature = useMemo(() => snapshotToJson(rubricProposal), [rubricProposal]);
  const sampleTemplateSignature = useMemo(() => snapshotToJson(sampleTemplateDraft), [sampleTemplateDraft]);
  const canLoadGeneratedSampleRubric = Boolean(
    sampleTemplateDraft &&
      rfqDraft &&
      rfqSignature === sampleTemplateSignature,
  );

  useEffect(() => {
    if (!initialisedRef.current || step !== "input" || !rfqDraft) {
      return;
    }
    if (rfqSignature === savedRfqRef.current) {
      return;
    }

    setAutosaveMessage("Saving RFQ draft...");
    const handle = window.setTimeout(async () => {
      try {
        const updated = await api.saveRfq(sessionId, rfqDraft);
        applySessionSnapshot(updated);
        savedRfqRef.current = snapshotToJson(updated.rfq_draft);
        setAutosaveMessage("RFQ draft saved");
      } catch {
        setAutosaveMessage("Autosave failed");
      }
    }, autosaveMs);

    return () => window.clearTimeout(handle);
  }, [api, autosaveMs, rfqDraft, rfqSignature, sessionId, step]);

  useEffect(() => {
    if (!initialisedRef.current || step === "input" || !rubricProposal || lockedArtifact) {
      return;
    }
    if (rubricSignature === savedRubricRef.current) {
      return;
    }

    setAutosaveMessage("Saving rubric edits...");
    const handle = window.setTimeout(async () => {
      try {
        const updated = await api.saveRubric(sessionId, rubricProposal);
        applySessionSnapshot(updated);
        savedRubricRef.current = snapshotToJson(updated.rubric_proposal);
        setAutosaveMessage("Rubric edits saved");
      } catch {
        setAutosaveMessage("Rubric autosave failed");
      }
    }, autosaveMs);

    return () => window.clearTimeout(handle);
  }, [api, autosaveMs, lockedArtifact, rubricProposal, rubricSignature, sessionId, step]);

  const canOpenProposal = Boolean(rubricProposal);
  const canOpenLock = Boolean(rubricProposal);
  const canOpenPack = Boolean(lockedArtifact && snapshot?.vendor_pack);
  const canOpenVendors = Boolean(lockedArtifact);
  const canOpenReview = Boolean(lockedArtifact);
  const canOpenResults = Boolean(lockedArtifact);

  async function handleGenerateRubric() {
    if (!rfqDraft) {
      return;
    }

    setIsGenerating(true);
    setRequestError(null);
    setValidationIssues([]);

    try {
      const updatedDraftSnapshot = await api.saveRfq(sessionId, rfqDraft);
      savedRfqRef.current = snapshotToJson(updatedDraftSnapshot.rfq_draft);
      applySessionSnapshot(updatedDraftSnapshot);

      const generatedSnapshot = await api.generateRubric(sessionId);
      applySessionSnapshot(generatedSnapshot);
      setRubricProposal(generatedSnapshot.rubric_proposal ?? null);
      savedRubricRef.current = snapshotToJson(generatedSnapshot.rubric_proposal);
      setAutosaveMessage("Rubric proposal generated");
      onStepChange("proposal");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to generate rubric.");
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleLoadGeneratedSampleRubric() {
    if (!canLoadGeneratedSampleRubric) {
      return;
    }

    setIsLoadingGeneratedSampleRubric(true);
    setRequestError(null);
    setValidationIssues([]);

    try {
      const archivedRubric = await api.getRubricTemplate("sample");
      const updated = await api.saveRubric(sessionId, archivedRubric);
      applySessionSnapshot(updated);
      setRubricProposal(updated.rubric_proposal ?? null);
      savedRubricRef.current = snapshotToJson(updated.rubric_proposal);
      setAutosaveMessage("Archived sample rubric loaded");
      onStepChange("proposal");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to load the archived sample rubric.");
    } finally {
      setIsLoadingGeneratedSampleRubric(false);
    }
  }

  async function handleLockRubric() {
    if (!rubricProposal) {
      return;
    }

    setIsLocking(true);
    setValidationIssues([]);
    setRequestError(null);

    try {
      if (rubricSignature !== savedRubricRef.current) {
        const updated = await api.saveRubric(sessionId, rubricProposal);
        applySessionSnapshot(updated);
        savedRubricRef.current = snapshotToJson(updated.rubric_proposal);
      }

      const artifact = await api.lockRubric(sessionId);
      const refreshed = await api.getSession(sessionId);
      applySessionSnapshot(refreshed);
      setLockedArtifact(artifact);
      setDownloadState("ready");
      setAutosaveMessage("Framework locked");
      onStepChange("lock");
    } catch (error) {
      if (error instanceof ApiError && error.status === 422) {
        setValidationIssues(normalizeValidationIssues(error.detail));
      } else {
        setRequestError(error instanceof Error ? error.message : "Failed to lock rubric.");
      }
    } finally {
      setIsLocking(false);
    }
  }

  async function handleDownloadArtifact() {
    setRequestError(null);

    try {
      const artifact = await api.downloadArtifact(sessionId);
      blobToDownload(artifact.blob, artifact.fileName);
      setDownloadState("done");
    } catch (error) {
      setDownloadState("error");
      setRequestError(error instanceof Error ? error.message : "Failed to download artifact.");
    }
  }

  async function handleDownloadVendorPack() {
    setRequestError(null);

    try {
      const vendorPack = await api.downloadVendorPack(sessionId);
      blobToDownload(vendorPack.blob, vendorPack.fileName);
      setVendorPackDownloadState("done");
    } catch (error) {
      setVendorPackDownloadState("error");
      setRequestError(error instanceof Error ? error.message : "Failed to download the vendor pack.");
    }
  }

  async function handleDownloadVendorDocument() {
    if (!lockedArtifact || !vendorPack) {
      return;
    }

    setRequestError(null);

    try {
      const vendorDocument = await buildVendorPackDocument(lockedArtifact, vendorPack);
      blobToDownload(vendorDocument.blob, vendorDocument.fileName);
      setVendorDocumentDownloadState("done");
    } catch (error) {
      setVendorDocumentDownloadState("error");
      setRequestError(error instanceof Error ? error.message : "Failed to download the vendor-facing RFQ document.");
    }
  }

  async function handleCreateVendor(name: string) {
    setRequestError(null);

    try {
      const updated = await api.createVendor(sessionId, name);
      applySessionSnapshot(updated);
      setAutosaveMessage("Vendor registered");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to create vendor.");
    }
  }

  async function handleRenameVendor(vendorId: string, name: string) {
    if (!name.trim()) {
      return;
    }

    setRequestError(null);
    try {
      const updated = await api.updateVendor(sessionId, vendorId, name.trim());
      applySessionSnapshot(updated);
      setAutosaveMessage("Vendor name updated");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to rename vendor.");
    }
  }

  async function handleDeleteVendor(vendorId: string) {
    setRequestError(null);
    try {
      const updated = await api.deleteVendor(sessionId, vendorId);
      applySessionSnapshot(updated);
      setAutosaveMessage("Vendor removed");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to delete vendor.");
    }
  }

  async function handleUploadVendorDocument(vendorId: string, file: File) {
    setUploadingVendorId(vendorId);
    setRequestError(null);

    try {
      const updated = await api.uploadVendorDocument(sessionId, vendorId, file);
      applySessionSnapshot(updated);
      setAutosaveMessage("Vendor document uploaded");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to upload vendor document.");
    } finally {
      setUploadingVendorId(null);
    }
  }

  async function handleExtractUploadedVendors() {
    setIsExtractingVendors(true);
    setRequestError(null);

    try {
      const updated = await api.extractUploadedVendors(sessionId);
      applySessionSnapshot(updated);
      setAutosaveMessage("Uploaded vendor extractions completed");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to extract uploaded vendor documents.");
    } finally {
      setIsExtractingVendors(false);
    }
  }

  async function handleRunEvaluation() {
    setIsRunningEvaluation(true);
    setRequestError(null);

    try {
      const report = await api.runEvaluation(sessionId);
      setEvaluationReport(report);
      const refreshed = await api.getSession(sessionId);
      applySessionSnapshot(refreshed);
      setAutosaveMessage("Evaluation completed");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to run the evaluation.");
    } finally {
      setIsRunningEvaluation(false);
    }
  }

  async function handleChangeReasoningEffort(reasoningEffort: ReasoningEffort) {
    const previous = cloneValue(llmSettingsDraft);
    const next = { reasoning_effort: reasoningEffort };
    setLlmSettingsDraft(next);
    setIsSavingLlmSettings(true);
    setRequestError(null);

    try {
      const updated = await api.saveLlmSettings(sessionId, reasoningEffort);
      applySessionSnapshot(updated);
      setAutosaveMessage(`LLM reasoning set to ${reasoningEffort}`);
    } catch (error) {
      setLlmSettingsDraft(previous);
      setRequestError(error instanceof Error ? error.message : "Failed to save LLM reasoning effort.");
    } finally {
      setIsSavingLlmSettings(false);
    }
  }

  async function handleApplyRfqTemplate(templateName: "blank" | "sample") {
    setIsApplyingTemplate(true);
    setRequestError(null);
    setValidationIssues([]);

    try {
      const templateDraft = await api.getRfqTemplate(templateName);
      const updated = await api.saveRfq(sessionId, templateDraft);
      applySessionSnapshot(updated);
      setRfqDraft(updated.rfq_draft);
      setRubricProposal(updated.rubric_proposal ?? null);
      setLockedArtifact(updated.locked_artifact ?? null);
      setEvaluationReport(updated.evaluation_report ?? null);
      savedRfqRef.current = snapshotToJson(updated.rfq_draft);
      savedRubricRef.current = snapshotToJson(updated.rubric_proposal);
      setAutosaveMessage(templateName === "sample" ? "Sample RFQ loaded" : "RFQ cleared");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to apply the RFQ template.");
    } finally {
      setIsApplyingTemplate(false);
    }
  }

  async function handleResetSession() {
    if (
      !window.confirm(
        "Start a fresh blank session? Your current work will remain only in the old session link.",
      )
    ) {
      return;
    }

    setIsResettingSession(true);
    setRequestError(null);
    setValidationIssues([]);

    try {
      const freshSession = await api.createOrHydrateSession();
      setStoredSessionId(freshSession.session_id);
      setAutosaveMessage("Fresh session ready");

      if (onSessionReplace) {
        onSessionReplace(freshSession.session_id, "input");
      } else {
        window.location.assign(`/rfq/${freshSession.session_id}?step=input`);
      }
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to reset the session.");
    } finally {
      setIsResettingSession(false);
    }
  }

  function updateDraft(mutator: (draft: RFQDraft) => void) {
    setRfqDraft((current: RFQDraft | null) => {
      if (!current) {
        return current;
      }
      const next = cloneValue(current);
      mutator(next);
      return next;
    });
  }

  function updateRubric(mutator: (proposal: RubricProposal) => void) {
    setRubricProposal((current: RubricProposal | null) => {
      if (!current) {
        return current;
      }
      const next = cloneValue(current);
      mutator(next);
      return next;
    });
  }

  if (isLoading) {
    return (
      <div className={styles.shell}>
        <div className={styles.frame}>
          <div className={`${styles.banner} ${styles.infoBanner}`}>Loading session...</div>
        </div>
      </div>
    );
  }

  if (!rfqDraft) {
    return (
      <div className={styles.shell}>
        <div className={styles.frame}>
          <div className={`${styles.banner} ${styles.errorBanner}`}>
            <strong>Request failed.</strong>{" "}
            {requestError ?? "No RFQ draft is available for this session."}
          </div>
          <div className={styles.buttonGroup}>
            <button
              className={styles.secondaryButton}
              onClick={() => window.location.reload()}
              type="button"
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  }

  const validationSummary =
    validationIssues.length > 0 ? (
      <div className={`${styles.banner} ${styles.errorBanner}`}>
        <strong>Lock validation failed.</strong>
        <div className={styles.validationList}>
          {validationIssues.map((issue) => (
            <div className={styles.validationItem} key={`${issue.field}-${issue.message}`}>
              <strong>{issue.field}</strong>: {issue.message}
            </div>
          ))}
        </div>
      </div>
    ) : null;

  const vendorPack: VendorPack | null = snapshot?.vendor_pack ?? null;
  const reviews = snapshot?.vendor_reviews ?? [];
  const normalizationReady = Boolean(snapshot?.comparison_settings);
  const currentEvaluationReport = evaluationReport ?? snapshot?.evaluation_report ?? null;

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.hero}>
          <div className={styles.eyebrow}>{lockedArtifact ? "Phase 2 Delivery" : "Phase 1 Delivery"}</div>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>
              {lockedArtifact ? "Locked Framework to Explainable Evaluation" : "RFQ to Locked Rubric"}
            </h1>
            <div className={styles.statusPill}>
              Status: {lockedArtifact ? "Locked" : snapshot?.status ?? "draft"}
            </div>
          </div>
          <p className={styles.subtitle}>
            {lockedArtifact
              ? "Preview the locked vendor pack, manage vendor uploads, review raw versus normalized evidence, and produce an explainable official QCBS 70/30 recommendation plus advisory scenarios."
              : "Start from a blank RFQ, optionally load the sample, generate an AI proposal, edit the framework, and lock the final rubric artifact for downstream evaluation phases."}
          </p>
          <div className={styles.meta}>
            <span>
              Session: <span className={styles.code}>{sessionId}</span>
            </span>
            <span>Last updated: {formatTimestamp(snapshot?.updated_at)}</span>
            <span className={styles.autosave}>{autosaveMessage}</span>
          </div>
          <div className={styles.heroControls}>
            <label className={styles.inlineField}>
              <span>LLM reasoning effort</span>
              <FormSelect
                className={styles.select}
                disabled={isSavingLlmSettings}
                onChange={(event) => void handleChangeReasoningEffort(event.target.value as ReasoningEffort)}
                value={llmSettingsDraft.reasoning_effort}
              >
                {REASONING_EFFORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </FormSelect>
            </label>
            <span className={styles.controlHint}>
              Applies to rubric generation, extraction, AI scoring, and AI scenarios.
            </span>
          </div>
          <div className={styles.heroActions}>
            <button
              className={styles.ghostButton}
              disabled={isResettingSession}
              onClick={handleResetSession}
              type="button"
            >
              {isResettingSession ? "Resetting..." : "Reset session"}
            </button>
          </div>
        </header>

        <nav className={styles.stepper} aria-label="RFQ wizard steps">
          <button
            className={`${styles.stepButton} ${step === "input" ? styles.activeStep : ""}`}
            onClick={() => onStepChange("input")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 1</span>
            <span className={styles.stepTitle}>RFQ Input</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "proposal" ? styles.activeStep : ""}`}
            disabled={!canOpenProposal}
            onClick={() => onStepChange("proposal")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 2</span>
            <span className={styles.stepTitle}>Proposal Review</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "lock" ? styles.activeStep : ""}`}
            disabled={!canOpenLock}
            onClick={() => onStepChange("lock")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 3</span>
            <span className={styles.stepTitle}>Lock & Export</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "pack" ? styles.activeStep : ""}`}
            disabled={!canOpenPack}
            onClick={() => onStepChange("pack")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 4</span>
            <span className={styles.stepTitle}>Vendor RFQ Pack</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "vendors" ? styles.activeStep : ""}`}
            disabled={!canOpenVendors}
            onClick={() => onStepChange("vendors")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 5</span>
            <span className={styles.stepTitle}>Add Vendors</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "review" ? styles.activeStep : ""}`}
            disabled={!canOpenReview}
            onClick={() => onStepChange("review")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 6</span>
            <span className={styles.stepTitle}>Run Extraction</span>
          </button>
          <button
            className={`${styles.stepButton} ${step === "results" ? styles.activeStep : ""}`}
            disabled={!canOpenResults}
            onClick={() => onStepChange("results")}
            type="button"
          >
            <span className={styles.stepLabel}>Step 7</span>
            <span className={styles.stepTitle}>Bidding Results</span>
          </button>
        </nav>

        {requestError ? (
          <div className={`${styles.banner} ${styles.errorBanner}`}>
            <strong>Request failed.</strong> {requestError}
          </div>
        ) : null}

        {validationSummary}

        {step === "input" ? (
            <InputStep
              canLoadGeneratedSampleRubric={canLoadGeneratedSampleRubric}
              draft={rfqDraft}
              isLoadingGeneratedSampleRubric={isLoadingGeneratedSampleRubric}
              onChange={updateDraft}
              onClear={() => void handleApplyRfqTemplate("blank")}
              onGenerate={handleGenerateRubric}
              onLoadGeneratedSampleRubric={handleLoadGeneratedSampleRubric}
              onUseSample={() => void handleApplyRfqTemplate("sample")}
              isApplyingTemplate={isApplyingTemplate}
              isGenerating={isGenerating}
            />
        ) : null}

        {step === "proposal" ? (
          rubricProposal ? (
            <ProposalStep
              proposal={rubricProposal}
              onChange={updateRubric}
              onBackToInput={() => onStepChange("input")}
              onReviewLock={() => onStepChange("lock")}
            />
          ) : (
            <div className={`${styles.banner} ${styles.infoBanner}`}>
              No rubric proposal is available yet. Generate one from the RFQ input step first.
            </div>
          )
        ) : null}

        {step === "lock" ? (
          rubricProposal ? (
            <LockStep
              draft={rfqDraft}
              proposal={rubricProposal}
              artifact={lockedArtifact}
              isLocking={isLocking}
              downloadState={downloadState}
              onBackToProposal={() => onStepChange("proposal")}
              onLock={handleLockRubric}
              onDownload={handleDownloadArtifact}
            />
          ) : (
            <div className={`${styles.banner} ${styles.infoBanner}`}>
              No rubric proposal is available yet. Generate and review a proposal before locking.
            </div>
          )
        ) : null}

        {step === "pack" ? (
          vendorPack && lockedArtifact ? (
            <PackStep
              artifact={lockedArtifact}
              downloadState={vendorPackDownloadState}
              onDownload={handleDownloadVendorPack}
              onDownloadVendorDocument={handleDownloadVendorDocument}
              vendorPack={vendorPack}
              vendorDocumentDownloadState={vendorDocumentDownloadState}
            />
          ) : (
            <div className={`${styles.banner} ${styles.infoBanner}`}>
              Lock the framework first to generate the vendor pack preview.
            </div>
          )
        ) : null}

        {step === "vendors" ? (
          <VendorsStep
            isExtractingVendors={isExtractingVendors}
            onCreateVendor={handleCreateVendor}
            onDeleteVendor={handleDeleteVendor}
            onExtractUploadedVendors={handleExtractUploadedVendors}
            onGoToReview={() => onStepChange("review")}
            onRenameVendor={handleRenameVendor}
            onUploadVendorDocument={handleUploadVendorDocument}
            uploadingVendorId={uploadingVendorId}
            vendors={snapshot?.vendors ?? []}
          />
        ) : null}

        {step === "review" ? (
          <ReviewStep
            artifact={lockedArtifact}
            comparisonSettings={snapshot?.comparison_settings ?? null}
            evaluationReport={currentEvaluationReport}
            onGoToResults={() => onStepChange("results")}
            onSelectVendor={setSelectedVendorId}
            reviews={reviews}
            selectedVendorId={selectedVendorId}
            vendors={snapshot?.vendors ?? []}
          />
        ) : null}

        {step === "results" ? (
          <ResultsStep
            artifact={lockedArtifact}
            comparisonSettings={snapshot?.comparison_settings ?? null}
            normalizationReady={normalizationReady}
            evaluationReport={currentEvaluationReport}
            isRunningEvaluation={isRunningEvaluation}
            onRunEvaluation={handleRunEvaluation}
            reviews={reviews}
          />
        ) : null}
      </div>
    </div>
  );
}

function InputStep({
  canLoadGeneratedSampleRubric,
  draft,
  isLoadingGeneratedSampleRubric,
  onChange,
  onClear,
  onGenerate,
  onLoadGeneratedSampleRubric,
  onUseSample,
  isApplyingTemplate,
  isGenerating,
}: {
  canLoadGeneratedSampleRubric: boolean;
  draft: RFQDraft;
  isLoadingGeneratedSampleRubric: boolean;
  onChange: (mutator: (draft: RFQDraft) => void) => void;
  onClear: () => void;
  onGenerate: () => void;
  onLoadGeneratedSampleRubric: () => void;
  onUseSample: () => void;
  isApplyingTemplate: boolean;
  isGenerating: boolean;
}) {
  return (
    <div className={styles.grid}>
      <div className={styles.buttonRow}>
        <div className={styles.meta}>
          <span>Build the RFQ manually, or load the full sample draft to start from the assignment example.</span>
        </div>
        <div className={styles.buttonGroup}>
          <button className={styles.secondaryButton} disabled={isApplyingTemplate} onClick={onUseSample} type="button">
            {isApplyingTemplate ? "Applying template..." : "Use RFQ Sample"}
          </button>
          <button
            className={styles.secondaryButton}
            disabled={!canLoadGeneratedSampleRubric || isApplyingTemplate || isGenerating || isLoadingGeneratedSampleRubric}
            onClick={onLoadGeneratedSampleRubric}
            type="button"
          >
            {isLoadingGeneratedSampleRubric ? "Loading generated rubric..." : "Load Generated Rubric"}
          </button>
          <button className={styles.ghostButton} disabled={isApplyingTemplate} onClick={onClear} type="button">
            Clear RFQ
          </button>
        </div>
      </div>
      <div className={styles.meta}>
        <span>
          The archived generated rubric is available only when the current RFQ exactly matches the built-in sample.
        </span>
      </div>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>General Information</h2>
            <p className={styles.cardSubtle}>
              Every field here is buyer-controlled. When priorities or mandatory conditions remain blank, the AI will infer them from the rest of the RFQ.
            </p>
          </div>
        </div>
        <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
          <label className={styles.label}>
            Subject
            <FormInput
              className={styles.input}
              value={draft.general_info.subject}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.subject = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            RFQ Code
            <FormInput
              className={styles.input}
              value={draft.general_info.rfq_code}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.rfq_code = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Sourcing Type
            <FormSelect
              className={styles.select}
              value={draft.general_info.sourcing_type}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.sourcing_type = event.target.value;
                })
              }
            >
              <option value="">Select sourcing type</option>
              <option value="RFQ">RFQ</option>
              <option value="RFP">RFP</option>
              <option value="RFI">RFI</option>
            </FormSelect>
          </label>
          <label className={styles.label}>
            Round
            <FormSelect
              className={styles.select}
              value={draft.general_info.round}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.round = event.target.value;
                })
              }
            >
              <option value="">Select round</option>
              <option value="Round 1">Round 1</option>
              <option value="Round 2">Round 2</option>
              <option value="Round 3">Round 3</option>
            </FormSelect>
          </label>
          <label className={styles.label}>
            Status
            <FormSelect
              className={styles.select}
              value={draft.general_info.status}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.status = event.target.value;
                })
              }
            >
              <option value="">Select status</option>
              <option value="Draft">Draft</option>
              <option value="Issued">Issued</option>
              <option value="Closed">Closed</option>
            </FormSelect>
          </label>
          <label className={styles.label}>
            Owner
            <FormInput
              className={styles.input}
              value={draft.general_info.owner}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.owner = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Currency
            <FormSelect
              className={styles.select}
              value={draft.general_info.currency}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.currency = event.target.value;
                })
              }
            >
              <option value="">Select currency</option>
              {SUPPORTED_RFQ_CURRENCIES.map((currencyCode) => (
                <option key={currencyCode} value={currencyCode}>
                  {currencyCode}
                </option>
              ))}
            </FormSelect>
          </label>
          <label className={styles.label}>
            Requestor
            <FormInput
              className={styles.input}
              value={draft.general_info.requestor}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.requestor = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Department
            <FormInput
              className={styles.input}
              value={draft.general_info.department}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.department = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Category
            <FormInput
              className={styles.input}
              value={draft.general_info.category}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.category = event.target.value;
                })
              }
            />
          </label>
        </div>
        <label className={styles.label} style={{ marginTop: 16 }}>
          Scope Overview
          <FormTextarea
            className={styles.textarea}
            value={draft.scope_overview}
            onChange={(event) =>
              onChange((current) => {
                current.scope_overview = event.target.value;
              })
            }
          />
        </label>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Timelines</h2>
            <p className={styles.cardSubtle}>Fill the milestone dates that matter for this RFQ. Leave blank if they are not yet known.</p>
          </div>
        </div>
        <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
          <label className={styles.label}>
            Clarifications Deadline
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.clarifications_deadline}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.clarifications_deadline = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Technical Bid Deadline
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.technical_bid_deadline}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.technical_bid_deadline = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Commercial Bid Deadline
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.commercial_bid_deadline}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.commercial_bid_deadline = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Evaluation Start Date
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.evaluation_start_date}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.evaluation_start_date = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Negotiation Start Date
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.negotiation_start_date}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.negotiation_start_date = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            Final Award Date
            <FormInput
              className={styles.input}
              type="date"
              value={draft.timelines.final_award_date}
              onChange={(event) =>
                onChange((current) => {
                  current.timelines.final_award_date = event.target.value;
                })
              }
            />
          </label>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Buyer Priorities</h2>
            <p className={styles.cardSubtle}>These priorities guide weighting and AI-generated questions. Leave blank to let the AI infer them.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.buyer_priorities.push(createBuyerPriority());
              })
            }
            type="button"
          >
            Add Priority
          </button>
        </div>
        <div className={styles.list}>
          {draft.buyer_priorities.map((priority: BuyerPriority, index: number) => (
            <div className={styles.itemCard} key={priority.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{priority.title || `Priority ${index + 1}`}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.buyer_priorities.splice(index, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
                <label className={styles.label}>
                  Title
                  <FormInput
                    className={styles.input}
                    value={priority.title}
                    onChange={(event) =>
                      onChange((current) => {
                        current.buyer_priorities[index].title = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Description
                  <FormInput
                    className={styles.input}
                    value={priority.description}
                    onChange={(event) =>
                      onChange((current) => {
                        current.buyer_priorities[index].description = event.target.value;
                      })
                    }
                  />
                </label>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Mandatory Conditions</h2>
            <p className={styles.cardSubtle}>These become likely MAC or cutoff-related evidence checks. Leave blank to let the AI infer them.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.mandatory_conditions.push("New mandatory condition");
              })
            }
            type="button"
          >
            Add Condition
          </button>
        </div>
        <div className={styles.list}>
          {draft.mandatory_conditions.map((condition: string, index: number) => (
            <div className={styles.itemCard} key={`${condition}-${index}`}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>Condition {index + 1}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.mandatory_conditions.splice(index, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <FormTextarea
                className={styles.textarea}
                value={condition}
                onChange={(event) =>
                  onChange((current) => {
                    current.mandatory_conditions[index] = event.target.value;
                  })
                }
              />
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>RFQ Line Items</h2>
            <p className={styles.cardSubtle}>
              Add the commercial line items you expect vendors to quote against. Use controlled UOMs only: Lot for services, Count for count-based items, and weight or volume units only when mathematical conversion should be allowed.
            </p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.line_items.push(createLineItem());
              })
            }
            type="button"
          >
            Add Line Item
          </button>
        </div>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Description</th>
                <th>HSN/SAC</th>
                <th>UOM</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {draft.line_items.map((item: LineItem, index: number) => (
                <tr key={item.id}>
                  <td>
                    <FormInput
                      className={styles.input}
                      value={item.product_name}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].product_name = event.target.value;
                        })
                      }
                    />
                  </td>
                  <td>
                    <FormInput
                      className={styles.input}
                      value={item.category}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].category = event.target.value;
                        })
                      }
                    />
                  </td>
                  <td>
                    <FormTextarea
                      className={styles.textarea}
                      value={item.description}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].description = event.target.value;
                        })
                      }
                    />
                  </td>
                  <td>
                    <FormInput
                      className={styles.input}
                      value={item.hsn_sac}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].hsn_sac = event.target.value;
                        })
                      }
                    />
                  </td>
                  <td>
                    <FormSelect
                      className={styles.select}
                      value={item.uom}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].uom = event.target.value;
                        })
                      }
                    >
                      <option value="">Select UOM</option>
                      {RFQ_UOM_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label} ({option.family})
                        </option>
                      ))}
                    </FormSelect>
                  </td>
                  <td>
                    <button
                      className={styles.dangerButton}
                      onClick={() =>
                        onChange((current) => {
                          current.line_items.splice(index, 1);
                        })
                      }
                      type="button"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className={styles.buttonRow}>
        <div className={styles.meta}>
          <span>The buyer can keep editing this draft until the framework is locked.</span>
        </div>
        <div className={styles.buttonGroup}>
          <button className={styles.primaryButton} disabled={isGenerating || isApplyingTemplate} onClick={onGenerate} type="button">
            {isGenerating ? "Generating rubric..." : "Generate AI rubric"}
          </button>
        </div>
      </div>
    </div>
  );
}

function ProposalStep({
  proposal,
  onChange,
  onBackToInput,
  onReviewLock,
}: {
  proposal: RubricProposal;
  onChange: (mutator: (proposal: RubricProposal) => void) => void;
  onBackToInput: () => void;
  onReviewLock: () => void;
}) {
  const scheduleFieldById = useMemo(
    () => buildScheduleFieldLookup(proposal.response_schedules),
    [proposal.response_schedules],
  );

  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Rubric Governance</h2>
            <p className={styles.cardSubtle}>
              The official award basis stays fixed to QCBS 70/30. The buyer can still edit threshold,
              criteria, questions, and schedules before lock.
            </p>
          </div>
        </div>
        <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
          <label className={styles.label}>
            Aggregate Technical Threshold
            <FormInput
              className={styles.input}
              type="number"
              value={proposal.aggregate_technical_threshold}
              onChange={(event) =>
                onChange((current) => {
                  current.aggregate_technical_threshold = Number(event.target.value || 0);
                })
              }
            />
          </label>
          <label className={styles.label}>
            Official Award Basis
            <FormInput className={styles.input} disabled value={proposal.official_award_basis} />
          </label>
          <label className={styles.label}>
            Generation Rationale
            <FormTextarea
              className={styles.textarea}
              value={proposal.generation_rationale.join("\n")}
              onChange={(event) =>
                onChange((current) => {
                  current.generation_rationale = event.target.value
                    .split("\n")
                    .map((item) => item.trim())
                    .filter(Boolean);
                })
              }
            />
          </label>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Sections</h2>
            <p className={styles.cardSubtle}>Moderate hierarchy: section, criterion, and evidence checks.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.sections.push(createSection());
              })
            }
            type="button"
          >
            Add Section
          </button>
        </div>
        <div className={styles.list}>
          {proposal.sections.map((section: RubricSection, index: number) => (
            <div className={styles.itemCard} key={section.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{section.title || `Section ${index + 1}`}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.sections.splice(index, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
                <label className={styles.label}>
                  Section ID
                  <FormInput
                    className={styles.input}
                    value={section.id}
                    onChange={(event) =>
                      onChange((current) => {
                        current.sections[index].id = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Title
                  <FormInput
                    className={styles.input}
                    value={section.title}
                    onChange={(event) =>
                      onChange((current) => {
                        current.sections[index].title = event.target.value;
                      })
                    }
                  />
                </label>
              </div>
              <label className={styles.label} style={{ marginTop: 12 }}>
                Description
                <FormTextarea
                  className={styles.textarea}
                  value={section.description}
                  onChange={(event) =>
                    onChange((current) => {
                      current.sections[index].description = event.target.value;
                    })
                  }
                />
              </label>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Criteria</h2>
            <p className={styles.cardSubtle}>
              Edit classifications, technical weights, cutoffs, evaluator checks, and the exact vendor-facing
              question that belongs to each non-commercial criterion.
            </p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                const sectionId = current.sections[0]?.id ?? "section_default";
                current.criteria.push(createCriterion(sectionId));
              })
            }
            type="button"
          >
            Add Criterion
          </button>
        </div>
        <div className={styles.list}>
          {proposal.criteria.map((criterion: Criterion, index: number) => (
            <CriterionEditor
              criterion={criterion}
              key={criterion.id}
              scheduleFieldById={scheduleFieldById}
              onChange={(mutator) =>
                onChange((current) => {
                  mutator(current.criteria[index]);
                })
              }
              onRemove={() =>
                onChange((current) => {
                  current.criteria.splice(index, 1);
                })
              }
            />
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Response Schedules</h2>
            <p className={styles.cardSubtle}>Structured schedules improve comparability without replacing narrative responses.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.response_schedules.push(createResponseSchedule());
              })
            }
            type="button"
          >
            Add Schedule
          </button>
        </div>
        <div className={styles.list}>
          {proposal.response_schedules.map((schedule: ResponseSchedule, index: number) => (
            <ScheduleEditor
              key={schedule.id}
              schedule={schedule}
              onChange={(mutator) =>
                onChange((current) => {
                  mutator(current.response_schedules[index]);
                })
              }
              onRemove={() =>
                onChange((current) => {
                  current.response_schedules.splice(index, 1);
                })
              }
            />
          ))}
        </div>
      </section>

      <div className={styles.buttonRow}>
        <div className={styles.buttonGroup}>
          <button className={styles.ghostButton} onClick={onBackToInput} type="button">
            Back to RFQ input
          </button>
        </div>
        <div className={styles.buttonGroup}>
          <button className={styles.primaryButton} onClick={onReviewLock} type="button">
            Review lock step
          </button>
        </div>
      </div>
    </div>
  );
}

function CriterionEditor({
  criterion,
  scheduleFieldById,
  onChange,
  onRemove,
}: {
  criterion: Criterion;
  scheduleFieldById: Map<string, ScheduleFieldPreview>;
  onChange: (mutator: (criterion: Criterion) => void) => void;
  onRemove: () => void;
}) {
  const vendorQuestion = criterion.vendor_question ?? null;
  const linkedScheduleFields: Array<{ id: string; field: ScheduleFieldPreview | null }> = (
    criterion.linked_schedule_fields ?? []
  ).map((fieldId: string) => ({
    id: fieldId,
    field: scheduleFieldById.get(fieldId) ?? null,
  }));
  const evidenceCheckCount = criterion.evidence_checks?.length ?? 0;

  return (
    <div className={styles.itemCard}>
      <div className={styles.itemHeader}>
        <div className={styles.itemTitle}>{criterion.title || criterion.id}</div>
        <button className={styles.dangerButton} onClick={onRemove} type="button">
          Remove
        </button>
      </div>
      <div className={styles.previewPanel}>
        <div className={styles.previewHeader}>
          <div>
            <div className={styles.previewEyebrow}>RFQ Creator View</div>
            <div className={styles.previewTitle}>Buyer-facing criterion view</div>
          </div>
          <div className={styles.previewBadge}>{formatCriterionMode(criterion)}</div>
        </div>

        <section className={`${styles.previewSection} ${styles.previewBox}`}>
          <div className={styles.previewSectionTitle}>Criterion summary</div>
          <div className={styles.summaryGrid}>
            <div className={styles.summaryItem}>
              <div className={styles.summaryLabel}>Criterion name</div>
              <div className={styles.summaryValue}>{criterion.title || criterion.id}</div>
            </div>
            <div className={styles.summaryItem}>
              <div className={styles.summaryLabel}>Evaluation mode</div>
              <div className={styles.summaryValue}>{formatCriterionTypeLabel(criterion.criterion_type)}</div>
            </div>
            <div className={styles.summaryItem}>
              <div className={styles.summaryLabel}>Technical weight</div>
              <div className={styles.summaryValue}>{formatCriterionWeight(criterion)}</div>
            </div>
            <div className={styles.summaryItem}>
              <div className={styles.summaryLabel}>Minimum qualifying score</div>
              <div className={styles.summaryValue}>{formatCriterionCutoff(criterion)}</div>
            </div>
            <div className={styles.summaryItem}>
              <div className={styles.summaryLabel}>Maximum score</div>
              <div className={styles.summaryValue}>{formatCriterionMaxScore(criterion)}</div>
            </div>
          </div>
          <div className={styles.summaryNarrative}>
            <div className={styles.summaryLabel}>What this criterion measures</div>
            <div className={styles.summaryValue}>
              {criterion.description || "No internal measurement statement has been added yet."}
            </div>
          </div>
        </section>

        <section className={`${styles.previewSection} ${styles.previewBox}`}>
          <div className={styles.previewSectionTitle}>
            {isTechnicalCriterion(criterion) ? "Primary vendor question" : "Vendor questionnaire"}
          </div>
          {vendorQuestion ? (
            <div className={styles.previewList}>
              <div className={styles.previewItem}>
                <div className={styles.previewItemHeader}>
                  <span className={styles.previewItemId}>{vendorQuestion.id}</span>
                  <span className={styles.previewItemMeta}>Vendor-facing question</span>
                </div>
                <div className={styles.previewItemBody}>{vendorQuestion.text}</div>
                <div className={styles.summaryLabel}>Why this question exists</div>
                <div className={styles.previewItemMeta}>{vendorQuestion.purpose || "No purpose note yet."}</div>
              </div>
            </div>
          ) : (
            <div className={styles.previewEmpty}>
              No exact vendor question is defined yet for this criterion.
            </div>
          )}
        </section>

        {usesQualitativeScoring(criterion) ? (
          <section className={`${styles.previewSection} ${styles.previewBox}`}>
            <div className={styles.previewSectionTitle}>AI judging guidance</div>
            <div className={styles.previewSummary}>
              {criterion.qualitative_scoring_guidance || "No qualitative scoring guidance is set yet."}
            </div>
          </section>
        ) : null}

        {linkedScheduleFields.length > 0 ? (
          <section className={`${styles.previewSection} ${styles.previewBox}`}>
            <div className={styles.previewSectionTitle}>Structured vendor inputs</div>
            <div className={styles.previewList}>
              {linkedScheduleFields.map(({ id, field }) => (
                <div className={styles.previewItem} key={id}>
                  {field ? (
                    <>
                      <div className={styles.previewItemHeader}>
                        <span className={styles.previewItemId}>{field.scheduleName}</span>
                        <span className={styles.previewItemMeta}>
                          {field.columnLabel} · {field.required ? "Required" : "Optional"}
                        </span>
                      </div>
                      <div className={styles.previewItemBody}>{field.description}</div>
                      <div className={styles.previewItemMeta}>{field.fieldId}</div>
                    </>
                  ) : (
                    <>
                      <div className={styles.previewItemHeader}>
                        <span className={styles.previewItemId}>{id}</span>
                        <span className={styles.previewItemMeta}>Unresolved schedule field</span>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </section>
        ) : null}

        <section className={`${styles.previewSection} ${styles.previewBox}`}>
          <DeterministicScoringPreview criterion={criterion} />
        </section>
      </div>
      <div className={styles.editorSection}>
        <div className={styles.editorSectionTitle}>Scoring setup</div>
        <div className={styles.editorSectionSubtle}>
          Define how this criterion behaves in technical or commercial evaluation.
        </div>
        <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
          <label className={styles.label}>
            Evaluation Mode
            <FormSelect
              className={styles.select}
              value={criterion.criterion_type}
              onChange={(event) =>
                onChange((current) => {
                  const nextType = event.target.value as CriterionType;
                  current.criterion_type = nextType;
                  if (nextType === "mac") {
                    current.weight = null;
                    current.min_cutoff = null;
                    current.max_score = null;
                    current.linked_schedule_fields = [];
                    current.qualitative_scoring_guidance = null;
                    current.vendor_question = current.vendor_question ?? {
                      id: current.linked_question_ids?.[0] ?? "",
                      text: "",
                      purpose: "",
                      linked_criteria: [current.id],
                    };
                    if (current.deterministic_scoring?.guide_type !== "pass_fail") {
                      current.deterministic_scoring = null;
                    }
                  } else if (nextType === "commercial") {
                    current.weight = null;
                    current.min_cutoff = null;
                    current.max_score = current.max_score ?? 10;
                    current.qualitative_scoring_guidance = null;
                    current.vendor_question = null;
                  } else if (nextType === "technical_scored_only") {
                    current.weight = current.weight ?? 0;
                    current.min_cutoff = null;
                    current.max_score = current.max_score ?? 10;
                    current.linked_schedule_fields = [];
                    current.vendor_question = current.vendor_question ?? {
                      id: current.linked_question_ids?.[0] ?? "",
                      text: "",
                      purpose: "",
                      linked_criteria: [current.id],
                    };
                  } else if (nextType === "technical_cutoff_backed") {
                    current.weight = current.weight ?? 0;
                    current.min_cutoff = current.min_cutoff ?? 0;
                    current.max_score = current.max_score ?? 10;
                    current.linked_schedule_fields = [];
                    current.vendor_question = current.vendor_question ?? {
                      id: current.linked_question_ids?.[0] ?? "",
                      text: "",
                      purpose: "",
                      linked_criteria: [current.id],
                    };
                  }
                })
              }
            >
              {CRITERION_TYPE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </FormSelect>
          </label>
          <label className={styles.label}>
            Technical Weight
            <FormInput
              className={styles.input}
              type="number"
              value={criterion.weight ?? ""}
              onChange={(event) =>
                onChange((current) => {
                  current.weight = parseNumber(event.target.value);
                })
              }
            />
          </label>
          <label className={styles.label}>
            Minimum Qualifying Score
            <FormInput
              className={styles.input}
              type="number"
              value={criterion.min_cutoff ?? ""}
              onChange={(event) =>
                onChange((current) => {
                  current.min_cutoff = parseNumber(event.target.value);
                })
              }
            />
          </label>
          <label className={styles.label}>
            Maximum Score
            <FormInput
              className={styles.input}
              type="number"
              value={criterion.max_score ?? ""}
              onChange={(event) =>
                onChange((current) => {
                  current.max_score = parseNumber(event.target.value);
                })
              }
            />
          </label>
        </div>
      </div>

      <div className={styles.editorSection}>
        <div className={styles.editorSectionTitle}>Vendor-facing question</div>
        <div className={styles.editorSectionSubtle}>
          This is the exact question that will be sent to the vendor for this non-commercial criterion.
        </div>
        {criterion.criterion_type === "commercial" ? (
          <div className={styles.previewEmpty}>
            Commercial criteria stay schedule-backed in the current model and do not own a vendor question.
          </div>
        ) : (
          <>
            <label className={styles.label}>
              Vendor Question Text
              <FormTextarea
                className={styles.textarea}
                value={vendorQuestion?.text ?? ""}
                onChange={(event) =>
                  onChange((current) => {
                    if (!current.vendor_question) {
                      current.vendor_question = {
                        id: current.linked_question_ids?.[0] ?? "",
                        text: "",
                        purpose: "",
                        linked_criteria: [current.id],
                      };
                    }
                    current.vendor_question.text = event.target.value;
                  })
                }
              />
            </label>
            <label className={styles.label}>
              Vendor Question Purpose
              <FormInput
                className={styles.input}
                value={vendorQuestion?.purpose ?? ""}
                onChange={(event) =>
                  onChange((current) => {
                    if (!current.vendor_question) {
                      current.vendor_question = {
                        id: current.linked_question_ids?.[0] ?? "",
                        text: "",
                        purpose: "",
                        linked_criteria: [current.id],
                      };
                    }
                    current.vendor_question.purpose = event.target.value;
                  })
                }
              />
            </label>
          </>
        )}
      </div>

      <div className={styles.editorSection}>
        <div className={styles.editorSectionTitle}>Criterion definition</div>
        <div className={styles.editorSectionSubtle}>
          This is the evaluator-facing definition of what the criterion is intended to judge.
        </div>
        <label className={styles.label}>
          Criterion Name
          <FormInput
            className={styles.input}
            value={criterion.title}
            onChange={(event) =>
              onChange((current) => {
                current.title = event.target.value;
              })
            }
          />
        </label>
        <label className={styles.label}>
          What This Criterion Measures
          <FormTextarea
            className={styles.textarea}
            value={criterion.description}
            onChange={(event) =>
              onChange((current) => {
                current.description = event.target.value;
              })
            }
          />
        </label>
        {usesQualitativeScoring(criterion) ? (
          <label className={styles.label} style={{ marginTop: 12 }}>
            Qualitative Scoring Guidance
            <FormTextarea
              className={styles.textarea}
              value={criterion.qualitative_scoring_guidance ?? ""}
              onChange={(event) =>
                onChange((current) => {
                  current.qualitative_scoring_guidance = event.target.value || null;
                })
              }
            />
          </label>
        ) : null}
      </div>

      <details className={styles.advancedPanel}>
        <summary className={styles.advancedSummary}>
          <span>Advanced traceability and evaluator checks</span>
          <span className={styles.advancedMeta}>
            {evidenceCheckCount} evaluator {evidenceCheckCount === 1 ? "check" : "checks"}
          </span>
        </summary>
        <div className={styles.advancedBody}>
          <div className={styles.editorSection}>
            <div className={styles.editorSectionTitle}>Internal mapping</div>
            <div className={styles.editorSectionSubtle}>
              Adjust these only when you need to change IDs or traceability links manually.
            </div>
            <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
              <label className={styles.label}>
                Internal Criterion ID
                <FormInput
                  className={styles.input}
                  value={criterion.id}
                  onChange={(event) =>
                    onChange((current) => {
                      current.id = event.target.value;
                      if (current.vendor_question) {
                        current.vendor_question.linked_criteria = [current.id];
                      }
                    })
                  }
                />
              </label>
              <label className={styles.label}>
                Internal Section ID
                <FormInput
                  className={styles.input}
                  value={criterion.section_id}
                  onChange={(event) =>
                    onChange((current) => {
                      current.section_id = event.target.value;
                    })
                  }
                />
              </label>
              {criterion.criterion_type !== "commercial" ? (
                <label className={styles.label}>
                  Internal Vendor Question ID
                  <FormInput
                    className={styles.input}
                    value={vendorQuestion?.id ?? ""}
                    onChange={(event) =>
                      onChange((current) => {
                        if (!current.vendor_question) {
                          current.vendor_question = {
                            id: "",
                            text: "",
                            purpose: "",
                            linked_criteria: [current.id],
                          };
                        }
                        current.vendor_question.id = event.target.value;
                      })
                    }
                  />
                </label>
              ) : null}
              {criterion.criterion_type === "commercial" ? (
                <label className={styles.label}>
                  Linked Structured Input Field IDs (comma separated)
                  <FormInput
                    className={styles.input}
                    value={toCsv(criterion.linked_schedule_fields)}
                    onChange={(event) =>
                      onChange((current) => {
                        current.linked_schedule_fields = parseCsv(event.target.value);
                      })
                    }
                  />
                </label>
              ) : null}
            </div>
          </div>

          <div className={styles.editorSection}>
            <div className={styles.itemHeader}>
              <div>
                <div className={styles.editorSectionTitle}>Evaluator checks</div>
                <div className={styles.editorSectionSubtle}>
                  These define what the evaluator must verify when qualifying or scoring this criterion.
                </div>
              </div>
              <button
                className={styles.secondaryButton}
                onClick={() =>
                  onChange((current) => {
                    current.evidence_checks = [...(current.evidence_checks ?? []), createEvidenceCheck()];
                  })
                }
                type="button"
              >
                Add Evaluator Check
              </button>
            </div>
            <div className={styles.list}>
              {(criterion.evidence_checks ?? []).map((evidence: EvidenceCheck, evidenceIndex: number) => (
                <div className={styles.itemCard} key={evidence.id}>
                  <div className={styles.itemHeader}>
                    <div className={styles.itemTitle}>{evidence.label || evidence.id}</div>
                    <button
                      className={styles.dangerButton}
                      onClick={() =>
                        onChange((current) => {
                          const evidenceChecks = current.evidence_checks ?? [];
                          evidenceChecks.splice(evidenceIndex, 1);
                          current.evidence_checks = evidenceChecks;
                        })
                      }
                      type="button"
                    >
                      Remove
                    </button>
                  </div>
                  <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
                    <label className={styles.label}>
                      Evaluator Check ID
                      <FormInput
                        className={styles.input}
                        value={evidence.id}
                        onChange={(event) =>
                          onChange((current) => {
                            const evidenceChecks = current.evidence_checks ?? [];
                            if (!evidenceChecks[evidenceIndex]) {
                              return;
                            }
                            evidenceChecks[evidenceIndex].id = event.target.value;
                            current.evidence_checks = evidenceChecks;
                          })
                        }
                      />
                    </label>
                    <label className={styles.label}>
                      Evaluator Check Name
                      <FormInput
                        className={styles.input}
                        value={evidence.label}
                        onChange={(event) =>
                          onChange((current) => {
                            const evidenceChecks = current.evidence_checks ?? [];
                            if (!evidenceChecks[evidenceIndex]) {
                              return;
                            }
                            evidenceChecks[evidenceIndex].label = event.target.value;
                            current.evidence_checks = evidenceChecks;
                          })
                        }
                      />
                    </label>
                  </div>
                  <label className={styles.label} style={{ marginTop: 12 }}>
                    What Evaluator Must Verify
                    <FormTextarea
                      className={styles.textarea}
                      value={evidence.description}
                      onChange={(event) =>
                        onChange((current) => {
                          const evidenceChecks = current.evidence_checks ?? [];
                          if (!evidenceChecks[evidenceIndex]) {
                            return;
                          }
                          evidenceChecks[evidenceIndex].description = event.target.value;
                          current.evidence_checks = evidenceChecks;
                        })
                      }
                    />
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}

function DeterministicScoringPreview({
  criterion,
}: {
  criterion: Criterion;
}) {
  const guide = criterion.deterministic_scoring;

  if (!guide) {
    const fallbackMessage =
      criterion.criterion_type === "mac"
        ? "No explicit rule table is defined yet. This criterion is currently treated as a mandatory pass/fail gate based on the linked evidence."
        : criterion.criterion_type === "commercial"
          ? "No explicit rule table is defined yet. This criterion is currently informational and intended for downstream commercial comparison."
          : "No explicit rule table is defined for this criterion. This criterion is expected to rely on AI judgement against the linked question, internal scoring guidance, and the score / cutoff settings shown above.";

    return (
      <div className={styles.previewSection}>
        <div className={styles.previewSectionTitle}>Scoring and qualifying rule</div>
        <div className={styles.previewEmpty}>{fallbackMessage}</div>
      </div>
    );
  }

  return (
    <div className={styles.previewSection}>
      <div className={styles.previewSectionTitle}>Scoring and qualifying rule</div>
      <div className={styles.previewSummary}>
        <strong>Answer format:</strong> {guide.answer_format}
        <span className={styles.previewSeparator}>·</span>
        <strong>Guide type:</strong> {formatGuideType(guide)}
      </div>
      <div className={styles.previewSummary}>{guide.summary}</div>
      <div className={styles.tableWrap}>
        <table className={styles.scoreTable}>
          <thead>
            <tr>
              <th>Response Condition</th>
              <th>Score / Outcome</th>
              <th>Max Score</th>
              <th>Cutoff</th>
            </tr>
          </thead>
          <tbody>
            {(guide.rules ?? []).map((rule: DeterministicScoringRule) => (
              <tr key={rule.id}>
                <td>{rule.condition}</td>
                <td>{formatScoringResult(rule)}</td>
                <td>{criterion.max_score ?? "N/A"}</td>
                <td>{criterion.min_cutoff ?? (criterion.criterion_type === "mac" ? "Pass/Fail" : "N/A")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatGuideType(guide: DeterministicScoringGuide): string {
  switch (guide.guide_type) {
    case "pass_fail":
      return "Pass / fail";
    case "numeric_banded":
      return "Numeric bands";
    case "discrete_banded":
      return "Discrete bands";
    default:
      return "Deterministic";
  }
}

function ScheduleEditor({
  schedule,
  onChange,
  onRemove,
}: {
  schedule: ResponseSchedule;
  onChange: (mutator: (schedule: ResponseSchedule) => void) => void;
  onRemove: () => void;
}) {
  return (
    <div className={styles.itemCard}>
      <div className={styles.itemHeader}>
        <div className={styles.itemTitle}>{schedule.name || schedule.id}</div>
        <button className={styles.dangerButton} onClick={onRemove} type="button">
          Remove
        </button>
      </div>
      <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
        <label className={styles.label}>
          Schedule ID
          <FormInput
            className={styles.input}
            value={schedule.id}
            onChange={(event) =>
              onChange((current) => {
                current.id = event.target.value;
              })
            }
          />
        </label>
        <label className={styles.label}>
          Schedule Name
          <FormInput
            className={styles.input}
            value={schedule.name}
            onChange={(event) =>
              onChange((current) => {
                current.name = event.target.value;
              })
            }
          />
        </label>
      </div>
      <label className={styles.label} style={{ marginTop: 12 }}>
        Purpose
        <FormTextarea
          className={styles.textarea}
          value={schedule.purpose}
          onChange={(event) =>
            onChange((current) => {
              current.purpose = event.target.value;
            })
          }
        />
      </label>
      <label className={styles.label} style={{ marginTop: 12 }}>
        Linked Criteria (comma separated IDs)
        <FormInput
          className={styles.input}
          value={toCsv(schedule.linked_criteria)}
          onChange={(event) =>
            onChange((current) => {
              current.linked_criteria = parseCsv(event.target.value);
            })
          }
        />
      </label>
      <div style={{ marginTop: 14 }}>
        <div className={styles.itemHeader}>
          <div className={styles.itemTitle}>Columns</div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.columns.push(createScheduleColumn());
              })
            }
            type="button"
          >
            Add Column
          </button>
        </div>
        <div className={styles.list}>
          {schedule.columns.map((column: ScheduleColumn, columnIndex: number) => (
            <div className={styles.itemCard} key={column.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{column.label || column.id}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.columns.splice(columnIndex, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
                <label className={styles.label}>
                  Column ID
                  <FormInput
                    className={styles.input}
                    value={column.id}
                    onChange={(event) =>
                      onChange((current) => {
                        current.columns[columnIndex].id = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Label
                  <FormInput
                    className={styles.input}
                    value={column.label}
                    onChange={(event) =>
                      onChange((current) => {
                        current.columns[columnIndex].label = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Required
                  <FormSelect
                    className={styles.select}
                    value={column.required ? "true" : "false"}
                    onChange={(event) =>
                      onChange((current) => {
                        current.columns[columnIndex].required = event.target.value === "true";
                      })
                    }
                  >
                    <option value="true">Required</option>
                    <option value="false">Optional</option>
                  </FormSelect>
                </label>
              </div>
              <label className={styles.label} style={{ marginTop: 12 }}>
                Description
                <FormTextarea
                  className={styles.textarea}
                  value={column.description}
                  onChange={(event) =>
                    onChange((current) => {
                      current.columns[columnIndex].description = event.target.value;
                    })
                  }
                />
              </label>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LockStep({
  draft,
  proposal,
  artifact,
  isLocking,
  downloadState,
  onBackToProposal,
  onLock,
  onDownload,
}: {
  draft: RFQDraft;
  proposal: RubricProposal;
  artifact: LockedFrameworkArtifact | null;
  isLocking: boolean;
  downloadState: "idle" | "ready" | "done" | "error";
  onBackToProposal: () => void;
  onLock: () => void;
  onDownload: () => void;
}) {
  const technicalCriteria = proposal.criteria.filter(
    (criterion: Criterion) =>
      criterion.criterion_type === "technical_cutoff_backed" ||
      criterion.criterion_type === "technical_scored_only",
  );
  const vendorQuestionCount = proposal.criteria.filter((criterion) => criterion.vendor_question).length;
  const artifactWarnings = artifact?.governance.rubric_warnings ?? [];

  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Lock Review</h2>
            <p className={styles.cardSubtle}>
              Review the governed framework before freezing it for downstream extraction and evaluation.
            </p>
          </div>
        </div>
        <div className={styles.summaryList}>
          <div className={styles.summaryItem}>
            <strong>RFQ</strong>: {draft.general_info.subject}
          </div>
          <div className={styles.summaryItem}>
            <strong>Official award basis</strong>: {proposal.official_award_basis}
          </div>
          <div className={styles.summaryItem}>
            <strong>Aggregate technical threshold</strong>: {proposal.aggregate_technical_threshold}
          </div>
          <div className={styles.summaryItem}>
            <strong>Technical criteria count</strong>: {technicalCriteria.length}
          </div>
          <div className={styles.summaryItem}>
            <strong>Questions</strong>: {vendorQuestionCount} | <strong>Schedules</strong>:{" "}
            {proposal.response_schedules.length}
          </div>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Ready To Lock</h2>
            <p className={styles.cardSubtle}>
              Locking freezes the framework artifact in the server-side session and enables download.
            </p>
          </div>
        </div>
        <div className={styles.buttonRow}>
          <div className={styles.buttonGroup}>
            <button className={styles.ghostButton} onClick={onBackToProposal} type="button">
              Back to proposal
            </button>
          </div>
          <div className={styles.buttonGroup}>
            <button className={styles.primaryButton} disabled={isLocking} onClick={onLock} type="button">
              {artifact ? "Framework locked" : isLocking ? "Locking..." : "Lock framework"}
            </button>
            <button
              className={styles.secondaryButton}
              disabled={!artifact}
              onClick={onDownload}
              type="button"
            >
              {downloadState === "done" ? "Download again" : "Download artifact JSON"}
            </button>
          </div>
        </div>
      </section>

      {artifact ? (
        <>
          <div className={`${styles.banner} ${styles.successBanner}`}>
            Framework locked successfully. The session now holds the frozen artifact for downstream phases.
          </div>
          {artifactWarnings.length > 0 ? (
            <div className={`${styles.banner} ${styles.infoBanner}`}>
              <strong>Rubric warnings were preserved on lock.</strong>
              <div className={styles.validationList}>
                {artifactWarnings.map((issue) => (
                  <div className={styles.validationItem} key={`${issue.field}-${issue.message}`}>
                    <strong>{issue.field}</strong>: {issue.message}
                  </div>
                ))}
              </div>
            </div>
          ) : null}
          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>Artifact Preview</h2>
                <p className={styles.cardSubtle}>
                  File name: <span className={styles.code}>{artifact.download_metadata.file_name}</span>
                </p>
              </div>
            </div>
            <pre className={styles.artifactPreview}>
              {JSON.stringify(artifact, null, 2)}
            </pre>
          </section>
        </>
      ) : (
        <div className={`${styles.banner} ${styles.infoBanner}`}>
          The framework is not locked yet. Use the lock action above to validate and freeze it.
        </div>
      )}
    </div>
  );
}
