"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import {
  ApiError,
  apiClient,
  type BuyerPriority,
  type RfqApiClient,
  type Criterion,
  type CriterionType,
  type EvidenceCheck,
  type LineItem,
  type LockedFrameworkArtifact,
  type Question,
  type RFQDraft,
  type ResponseSchedule,
  type RubricSection,
  type RubricProposal,
  type ScheduleColumn,
  type SessionSnapshot,
  type TimelineItem,
  type ValidationIssue,
} from "@/lib/api";
import {
  CRITERION_TYPE_OPTIONS,
  cloneValue,
  createBuyerPriority,
  createCriterion,
  createEvidenceCheck,
  createLineItem,
  createQuestion,
  createResponseSchedule,
  createScheduleColumn,
  createSection,
  createTimelineItem,
  parseCsv,
  toCsv,
} from "@/lib/rubric-factories";

import styles from "./rfq-wizard.module.css";

export type WizardStep = "input" | "proposal" | "lock";

const DEFAULT_AUTOSAVE_MS = 700;

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

type RfqWizardProps = {
  sessionId: string;
  step: WizardStep;
  onStepChange: (step: WizardStep) => void;
  api?: RfqApiClient;
  autosaveMs?: number;
};

export function RfqWizard({
  sessionId,
  step,
  onStepChange,
  api = apiClient,
  autosaveMs = DEFAULT_AUTOSAVE_MS,
}: RfqWizardProps) {
  const [snapshot, setSnapshot] = useState<SessionSnapshot | null>(null);
  const [rfqDraft, setRfqDraft] = useState<RFQDraft | null>(null);
  const [rubricProposal, setRubricProposal] = useState<RubricProposal | null>(null);
  const [lockedArtifact, setLockedArtifact] = useState<LockedFrameworkArtifact | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isLocking, setIsLocking] = useState(false);
  const [requestError, setRequestError] = useState<string | null>(null);
  const [validationIssues, setValidationIssues] = useState<ValidationIssue[]>([]);
  const [autosaveMessage, setAutosaveMessage] = useState("Waiting for changes");
  const [downloadState, setDownloadState] = useState<"idle" | "ready" | "done" | "error">("idle");

  const initialisedRef = useRef(false);
  const savedRfqRef = useRef("");
  const savedRubricRef = useRef("");

  useEffect(() => {
    let cancelled = false;

    async function loadSession() {
      setIsLoading(true);
      setRequestError(null);

      try {
        const loaded = await api.getSession(sessionId);
        if (cancelled) {
          return;
        }

        setSnapshot(loaded);
        setRfqDraft(loaded.rfq_draft);
        setRubricProposal(loaded.rubric_proposal ?? null);
        setLockedArtifact(loaded.locked_artifact ?? null);
        setDownloadState(loaded.locked_artifact ? "ready" : "idle");
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

  const rfqSignature = useMemo(() => snapshotToJson(rfqDraft), [rfqDraft]);
  const rubricSignature = useMemo(() => snapshotToJson(rubricProposal), [rubricProposal]);

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
        setSnapshot(updated);
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
        setSnapshot(updated);
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
      setSnapshot(updatedDraftSnapshot);

      const generatedSnapshot = await api.generateRubric(sessionId);
      setSnapshot(generatedSnapshot);
      setRubricProposal(generatedSnapshot.rubric_proposal ?? null);
      setLockedArtifact(generatedSnapshot.locked_artifact ?? null);
      savedRubricRef.current = snapshotToJson(generatedSnapshot.rubric_proposal);
      setAutosaveMessage("Rubric proposal generated");
      onStepChange("proposal");
    } catch (error) {
      setRequestError(error instanceof Error ? error.message : "Failed to generate rubric.");
    } finally {
      setIsGenerating(false);
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
        setSnapshot(updated);
        savedRubricRef.current = snapshotToJson(updated.rubric_proposal);
      }

      const artifact = await api.lockRubric(sessionId);
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

  if (isLoading || !rfqDraft) {
    return (
      <div className={styles.shell}>
        <div className={styles.frame}>
          <div className={`${styles.banner} ${styles.infoBanner}`}>Loading session...</div>
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

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.hero}>
          <div className={styles.eyebrow}>Phase 1 Delivery</div>
          <div className={styles.titleRow}>
            <h1 className={styles.title}>RFQ to Locked Rubric</h1>
            <div className={styles.statusPill}>
              Status: {lockedArtifact ? "Locked" : snapshot?.status ?? "draft"}
            </div>
          </div>
          <p className={styles.subtitle}>
            Start from the seeded 8-item RFQ, generate an AI proposal, edit the framework, and lock
            the final rubric artifact for downstream evaluation phases.
          </p>
          <div className={styles.meta}>
            <span>
              Session: <span className={styles.code}>{sessionId}</span>
            </span>
            <span>Last updated: {formatTimestamp(snapshot?.updated_at)}</span>
            <span className={styles.autosave}>{autosaveMessage}</span>
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
        </nav>

        {requestError ? (
          <div className={`${styles.banner} ${styles.errorBanner}`}>
            <strong>Request failed.</strong> {requestError}
          </div>
        ) : null}

        {validationSummary}

        {step === "input" ? (
          <InputStep
            draft={rfqDraft}
            onChange={updateDraft}
            onGenerate={handleGenerateRubric}
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
      </div>
    </div>
  );
}

function InputStep({
  draft,
  onChange,
  onGenerate,
  isGenerating,
}: {
  draft: RFQDraft;
  onChange: (mutator: (draft: RFQDraft) => void) => void;
  onGenerate: () => void;
  isGenerating: boolean;
}) {
  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>General Information</h2>
            <p className={styles.cardSubtle}>
              The seeded sample is editable. Any change here feeds the AI rubric proposal.
            </p>
          </div>
        </div>
        <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
          <label className={styles.label}>
            RFQ Title
            <input
              className={styles.input}
              value={draft.general_info.title}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.title = event.target.value;
                })
              }
            />
          </label>
          <label className={styles.label}>
            RFQ Code
            <input
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
            Owner
            <input
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
            Region
            <input
              className={styles.input}
              value={draft.general_info.region}
              onChange={(event) =>
                onChange((current) => {
                  current.general_info.region = event.target.value;
                })
              }
            />
          </label>
        </div>
        <label className={styles.label} style={{ marginTop: 16 }}>
          Scope Overview
          <textarea
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
            <p className={styles.cardSubtle}>These dates help the AI decide threshold and timeline evidence.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.timelines.push(createTimelineItem());
              })
            }
            type="button"
          >
            Add Timeline
          </button>
        </div>
        <div className={styles.list}>
          {draft.timelines.map((timeline: TimelineItem, index: number) => (
            <div className={styles.itemCard} key={timeline.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{timeline.label || `Timeline ${index + 1}`}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.timelines.splice(index, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
                <label className={styles.label}>
                  Label
                  <input
                    className={styles.input}
                    value={timeline.label}
                    onChange={(event) =>
                      onChange((current) => {
                        current.timelines[index].label = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Target Date
                  <input
                    className={styles.input}
                    value={timeline.target_date}
                    onChange={(event) =>
                      onChange((current) => {
                        current.timelines[index].target_date = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Description
                  <input
                    className={styles.input}
                    value={timeline.description}
                    onChange={(event) =>
                      onChange((current) => {
                        current.timelines[index].description = event.target.value;
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
            <h2 className={styles.cardTitle}>Buyer Priorities</h2>
            <p className={styles.cardSubtle}>These priorities guide weighting and AI-generated questions.</p>
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
                  <input
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
                  <input
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
            <p className={styles.cardSubtle}>These become likely MAC or cutoff-related evidence checks.</p>
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
              <textarea
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
            <p className={styles.cardSubtle}>All eight seeded items are editable and additional items can be added.</p>
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
                    <input
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
                    <input
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
                    <textarea
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
                    <input
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
                    <input
                      className={styles.input}
                      value={item.uom}
                      onChange={(event) =>
                        onChange((current) => {
                          current.line_items[index].uom = event.target.value;
                        })
                      }
                    />
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
          <button className={styles.primaryButton} disabled={isGenerating} onClick={onGenerate} type="button">
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
            <input
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
            <input className={styles.input} disabled value={proposal.official_award_basis} />
          </label>
          <label className={styles.label}>
            Generation Rationale
            <textarea
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
                  <input
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
                  <input
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
                <textarea
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
              Edit classifications, technical weights, cutoffs, evidence links, and linked questions or
              schedule fields.
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
            <h2 className={styles.cardTitle}>Questions</h2>
            <p className={styles.cardSubtle}>Questions should gather evidence for the rubric, not stand alone.</p>
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.questions.push(createQuestion());
              })
            }
            type="button"
          >
            Add Question
          </button>
        </div>
        <div className={styles.list}>
          {proposal.questions.map((question: Question, index: number) => (
            <div className={styles.itemCard} key={question.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{question.id}</div>
                <button
                  className={styles.dangerButton}
                  onClick={() =>
                    onChange((current) => {
                      current.questions.splice(index, 1);
                    })
                  }
                  type="button"
                >
                  Remove
                </button>
              </div>
              <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
                <label className={styles.label}>
                  Question ID
                  <input
                    className={styles.input}
                    value={question.id}
                    onChange={(event) =>
                      onChange((current) => {
                        current.questions[index].id = event.target.value;
                      })
                    }
                  />
                </label>
                <label className={styles.label}>
                  Linked Criteria (comma separated IDs)
                  <input
                    className={styles.input}
                    value={toCsv(question.linked_criteria)}
                    onChange={(event) =>
                      onChange((current) => {
                        current.questions[index].linked_criteria = parseCsv(event.target.value);
                      })
                    }
                  />
                </label>
              </div>
              <label className={styles.label} style={{ marginTop: 12 }}>
                Question Text
                <textarea
                  className={styles.textarea}
                  value={question.text}
                  onChange={(event) =>
                    onChange((current) => {
                      current.questions[index].text = event.target.value;
                    })
                  }
                />
              </label>
              <label className={styles.label} style={{ marginTop: 12 }}>
                Purpose
                <input
                  className={styles.input}
                  value={question.purpose}
                  onChange={(event) =>
                    onChange((current) => {
                      current.questions[index].purpose = event.target.value;
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
  onChange,
  onRemove,
}: {
  criterion: Criterion;
  onChange: (mutator: (criterion: Criterion) => void) => void;
  onRemove: () => void;
}) {
  return (
    <div className={styles.itemCard}>
      <div className={styles.itemHeader}>
        <div className={styles.itemTitle}>{criterion.title || criterion.id}</div>
        <button className={styles.dangerButton} onClick={onRemove} type="button">
          Remove
        </button>
      </div>
      <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
        <label className={styles.label}>
          Criterion ID
          <input
            className={styles.input}
            value={criterion.id}
            onChange={(event) =>
              onChange((current) => {
                current.id = event.target.value;
              })
            }
          />
        </label>
        <label className={styles.label}>
          Section ID
          <input
            className={styles.input}
            value={criterion.section_id}
            onChange={(event) =>
              onChange((current) => {
                current.section_id = event.target.value;
              })
            }
          />
        </label>
        <label className={styles.label}>
          Criterion Type
          <select
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
                } else if (nextType === "commercial") {
                  current.weight = null;
                  current.min_cutoff = null;
                  current.max_score = current.max_score ?? 10;
                } else if (nextType === "technical_scored_only") {
                  current.weight = current.weight ?? 0;
                  current.min_cutoff = null;
                  current.max_score = current.max_score ?? 10;
                } else if (nextType === "technical_cutoff_backed") {
                  current.weight = current.weight ?? 0;
                  current.min_cutoff = current.min_cutoff ?? 0;
                  current.max_score = current.max_score ?? 10;
                }
              })
            }
          >
            {CRITERION_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className={styles.label}>
          Weight
          <input
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
          Min Cutoff
          <input
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
          Max Score
          <input
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
      <label className={styles.label} style={{ marginTop: 12 }}>
        Title
        <input
          className={styles.input}
          value={criterion.title}
          onChange={(event) =>
            onChange((current) => {
              current.title = event.target.value;
            })
          }
        />
      </label>
      <label className={styles.label} style={{ marginTop: 12 }}>
        Description
        <textarea
          className={styles.textarea}
          value={criterion.description}
          onChange={(event) =>
            onChange((current) => {
              current.description = event.target.value;
            })
          }
        />
      </label>
      <div className={`${styles.fieldGrid} ${styles.twoCol}`} style={{ marginTop: 12 }}>
        <label className={styles.label}>
          Linked Question IDs (comma separated)
          <input
            className={styles.input}
            value={toCsv(criterion.linked_question_ids)}
            onChange={(event) =>
              onChange((current) => {
                current.linked_question_ids = parseCsv(event.target.value);
              })
            }
          />
        </label>
        <label className={styles.label}>
          Linked Schedule Fields (comma separated)
          <input
            className={styles.input}
            value={toCsv(criterion.linked_schedule_fields)}
            onChange={(event) =>
              onChange((current) => {
                current.linked_schedule_fields = parseCsv(event.target.value);
              })
            }
          />
        </label>
      </div>
      <div style={{ marginTop: 14 }}>
        <div className={styles.itemHeader}>
          <div className={styles.itemTitle}>Evidence Checks</div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChange((current) => {
                current.evidence_checks = [...(current.evidence_checks ?? []), createEvidenceCheck()];
              })
            }
            type="button"
          >
            Add Evidence Check
          </button>
        </div>
        <div className={styles.list}>
          {(criterion.evidence_checks ?? []).map((evidence: EvidenceCheck, evidenceIndex: number) => (
            <div className={styles.itemCard} key={evidence.id}>
              <div className={styles.itemHeader}>
                <div className={styles.itemTitle}>{evidence.id}</div>
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
                  Check ID
                  <input
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
                  Label
                  <input
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
                Description
                <textarea
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
  );
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
          <input
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
          <input
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
        <textarea
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
        <input
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
                  <input
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
                  <input
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
                  <select
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
                  </select>
                </label>
              </div>
              <label className={styles.label} style={{ marginTop: 12 }}>
                Description
                <textarea
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
            <strong>RFQ</strong>: {draft.general_info.title}
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
            <strong>Questions</strong>: {proposal.questions.length} | <strong>Schedules</strong>:{" "}
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
