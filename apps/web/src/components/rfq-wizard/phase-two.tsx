"use client";

import { useEffect, useMemo, useState } from "react";

import type {
  ComparisonSettings,
  ExtractedField,
  EvaluationReport,
  FXRate,
  LockedFrameworkArtifact,
  NormalizedField,
  NormalizedPricingLine,
  UomOverride,
  VendorPack,
  VendorRecord,
  VendorReview,
} from "@/lib/api";

import styles from "./rfq-wizard.module.css";

type DownloadState = "idle" | "ready" | "done" | "error";

type PackStepProps = {
  artifact: LockedFrameworkArtifact;
  vendorPack: VendorPack;
  downloadState: DownloadState;
  vendorDocumentDownloadState: DownloadState;
  onDownload: () => void;
  onDownloadVendorDocument: () => void;
};

type VendorsStepProps = {
  vendors: VendorRecord[];
  uploadingVendorId: string | null;
  extractingVendorId: string | null;
  onCreateVendor: (name: string) => void;
  onRenameVendor: (vendorId: string, name: string) => void;
  onDeleteVendor: (vendorId: string) => void;
  onUploadVendorDocument: (vendorId: string, file: File) => void;
  onExtractVendor: (vendorId: string) => void;
  onGoToReview: () => void;
};

type ReviewStepProps = {
  vendors: VendorRecord[];
  reviews: VendorReview[];
  selectedVendorId: string | null;
  comparisonSettingsDraft: ComparisonSettings;
  isSavingComparison: boolean;
  onSelectVendor: (vendorId: string) => void;
  onChangeComparison: (mutator: (current: ComparisonSettings) => void) => void;
  onSaveComparison: () => void;
  onGoToResults: () => void;
};

type ResultsStepProps = {
  evaluationReport: EvaluationReport | null;
  comparisonSettingsReady: boolean;
  isRunningEvaluation: boolean;
  onRunEvaluation: () => void;
};

const ACCEPTED_VENDOR_FILES = ".pdf,.ppt,.pptx,.doc,.docx,.xls,.xlsx";

export function PackStep({
  artifact,
  vendorPack,
  downloadState,
  vendorDocumentDownloadState,
  onDownload,
  onDownloadVendorDocument,
}: PackStepProps) {
  const responseInstructions = vendorPack.response_instructions ?? [];
  const questions = vendorPack.questions ?? [];
  const schedules = vendorPack.response_schedules ?? [];
  const criteria = vendorPack.criteria ?? [];
  const lineItems = artifact.rfq_snapshot.line_items ?? [];

  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Vendor Pack Preview</h2>
            <p className={styles.cardSubtle}>
              This is the buyer-approved vendor-facing pack derived directly from the locked framework.
            </p>
          </div>
          <div className={styles.buttonGroup}>
            <button className={styles.secondaryButton} onClick={onDownloadVendorDocument} type="button">
              {vendorDocumentDownloadState === "done" ? "Download vendor RFQ again" : "Download vendor RFQ (.docx)"}
            </button>
            <button className={styles.secondaryButton} onClick={onDownload} type="button">
              {downloadState === "done" ? "Download pack again" : "Download pack JSON"}
            </button>
          </div>
        </div>

        <div className={styles.summaryGrid}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>RFQ</span>
            <span className={styles.summaryValue}>{vendorPack.rfq_title}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>RFQ Code</span>
            <span className={styles.summaryValue}>{artifact.rfq_snapshot.general_info.rfq_code}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Questions</span>
            <span className={styles.summaryValue}>{questions.length}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Schedules</span>
            <span className={styles.summaryValue}>{schedules.length}</span>
          </div>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Vendor Export Scope</h2>
            <p className={styles.cardSubtle}>
              The `.docx` export includes RFQ header details, scope, timelines, line items, response instructions,
              exact questionnaire text, and schedules. It excludes internal scoring logic, thresholds, and evaluator
              linkages.
            </p>
          </div>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Response Instructions</h2>
            <p className={styles.cardSubtle}>The vendor sees these instructions before answering the pack.</p>
          </div>
        </div>
        <div className={styles.previewList}>
          {responseInstructions.map((instruction, index) => (
            <div className={styles.previewItem} key={`${instruction}-${index}`}>
              <div className={styles.previewItemBody}>{instruction}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Exact Vendor Questions</h2>
            <p className={styles.cardSubtle}>
              This is the exact questionnaire text the vendor is expected to answer.
            </p>
          </div>
        </div>
        <div className={styles.previewList}>
          {questions.map((question) => (
            <div className={styles.previewItem} key={question.id}>
              <div className={styles.previewItemHeader}>
                <div className={styles.previewItemId}>{question.id}</div>
                <div className={styles.previewItemMeta}>
                  Linked criteria: {(question.linked_criteria ?? []).join(", ") || "None"}
                </div>
              </div>
              <div className={styles.previewItemBody}>{question.text}</div>
              <div className={styles.previewItemMeta}>Purpose: {question.purpose}</div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Requested Schedules</h2>
            <p className={styles.cardSubtle}>
              Structured schedule columns are shown here exactly as the vendor must provide them.
            </p>
          </div>
        </div>
        <div className={styles.previewList}>
          {schedules.map((schedule) => (
            <div className={styles.previewItem} key={schedule.id}>
              <div className={styles.previewItemHeader}>
                <div>
                  <div className={styles.previewItemId}>{schedule.id}</div>
                  <div className={styles.previewTitle}>{schedule.name}</div>
                </div>
                <div className={styles.previewItemMeta}>
                  Linked criteria: {(schedule.linked_criteria ?? []).join(", ") || "None"}
                </div>
              </div>
              <div className={styles.previewItemMeta}>{schedule.purpose}</div>
              <div className={styles.tableWrap}>
                <table className={styles.scoreTable}>
                  <thead>
                    <tr>
                      <th>Field</th>
                      <th>Label</th>
                      <th>Description</th>
                      <th>Required</th>
                      <th>Linked Criteria</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(schedule.columns ?? []).map((column) => (
                      <tr key={column.field_id}>
                        <td>{column.field_id}</td>
                        <td>{column.label}</td>
                        <td>{column.description}</td>
                        <td>{column.required ? "Yes" : "No"}</td>
                        <td>{(column.linked_criteria ?? []).join(", ") || "None"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Requested Line Items</h2>
            <p className={styles.cardSubtle}>
              These line items are included in the vendor-facing document alongside the questionnaire.
            </p>
          </div>
        </div>
        <div className={styles.tableWrap}>
          <table className={styles.scoreTable}>
            <thead>
              <tr>
                <th>ID</th>
                <th>Line Item</th>
                <th>Category</th>
                <th>UOM</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {lineItems.map((lineItem) => (
                <tr key={lineItem.id}>
                  <td>{lineItem.id}</td>
                  <td>{lineItem.product_name}</td>
                  <td>{lineItem.category}</td>
                  <td>{lineItem.uom}</td>
                  <td>{lineItem.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Criteria Linkages</h2>
            <p className={styles.cardSubtle}>
              This view is internal only. It helps the buyer trace the pack back to the locked evaluation framework and
              is not included in the vendor-facing document export.
            </p>
          </div>
        </div>
        <div className={styles.previewList}>
          {criteria.map((criterion) => (
            <div className={styles.previewItem} key={criterion.criterion_id}>
              <div className={styles.previewItemHeader}>
                <div>
                  <div className={styles.previewItemId}>{criterion.criterion_id}</div>
                  <div className={styles.previewTitle}>{criterion.title}</div>
                </div>
                <div className={styles.previewBadge}>{criterion.criterion_type}</div>
              </div>
              <div className={styles.previewItemBody}>{criterion.description}</div>
              <div className={styles.previewItemMeta}>
                Questions: {(criterion.linked_question_ids ?? []).join(", ") || "None"}
              </div>
              <div className={styles.previewItemMeta}>
                Schedule fields: {(criterion.linked_schedule_fields ?? []).join(", ") || "None"}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Pack JSON Preview</h2>
            <p className={styles.cardSubtle}>A direct JSON handoff is also available for downstream processing.</p>
          </div>
        </div>
        <pre className={styles.artifactPreview}>{JSON.stringify(vendorPack, null, 2)}</pre>
      </section>
    </div>
  );
}

export function VendorsStep({
  vendors,
  uploadingVendorId,
  extractingVendorId,
  onCreateVendor,
  onRenameVendor,
  onDeleteVendor,
  onUploadVendorDocument,
  onExtractVendor,
  onGoToReview,
}: VendorsStepProps) {
  const [newVendorName, setNewVendorName] = useState("");
  const [renameDrafts, setRenameDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    setRenameDrafts((current) => {
      const next = { ...current };
      for (const vendor of vendors) {
        next[vendor.id] ??= vendor.name;
      }
      return next;
    });
  }, [vendors]);

  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Vendor Registry</h2>
            <p className={styles.cardSubtle}>
              Register vendors here. Each vendor gets exactly one replaceable source document in this phase.
            </p>
          </div>
        </div>
        <div className={styles.vendorToolbar}>
          <input
            className={styles.input}
            name="new_vendor_name"
            placeholder="Add vendor name"
            value={newVendorName}
            onChange={(event) => setNewVendorName(event.target.value)}
          />
          <button
            className={styles.primaryButton}
            onClick={() => {
              const name = newVendorName.trim();
              if (!name) {
                return;
              }
              onCreateVendor(name);
              setNewVendorName("");
            }}
            type="button"
          >
            Add vendor
          </button>
          <button className={styles.secondaryButton} onClick={onGoToReview} type="button">
            Go to review
          </button>
        </div>
      </section>

      {vendors.length === 0 ? (
        <div className={`${styles.banner} ${styles.infoBanner}`}>
          No vendors have been registered yet. Add at least one vendor to continue.
        </div>
      ) : null}

      <div className={styles.list}>
        {vendors.map((vendor) => (
          <div className={styles.itemCard} key={vendor.id}>
            <div className={styles.itemHeader}>
              <div>
                <div className={styles.itemTitle}>{vendor.name}</div>
                <div className={styles.previewItemMeta}>{vendor.id}</div>
              </div>
              <div className={`${styles.statusBadge} ${statusClassName(vendor.status ?? "no_document")}`}>
                {vendor.status ?? "no_document"}
              </div>
            </div>

            <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
              <label className={styles.label}>
                Vendor Name
                <input
                  className={styles.input}
                  name={`vendor_name_${vendor.id}`}
                  value={renameDrafts[vendor.id] ?? vendor.name}
                  onChange={(event) =>
                    setRenameDrafts((current) => ({
                      ...current,
                      [vendor.id]: event.target.value,
                    }))
                  }
                />
              </label>
              <div className={styles.label}>
                Current Document
                <div className={styles.staticBox}>
                  {vendor.document ? vendor.document.file_name : "No document uploaded"}
                </div>
              </div>
              <div className={styles.label}>
                Last Extraction
                <div className={styles.staticBox}>{formatTimestamp(vendor.last_extracted_at ?? null)}</div>
              </div>
            </div>

            {(vendor.warnings ?? []).length > 0 ? (
              <div className={`${styles.banner} ${styles.infoBanner}`} style={{ marginTop: 12 }}>
                {(vendor.warnings ?? []).join(" ")}
              </div>
            ) : null}

            {vendor.extraction_error ? (
              <div className={`${styles.banner} ${styles.errorBanner}`} style={{ marginTop: 12 }}>
                {vendor.extraction_error}
              </div>
            ) : null}

            <div className={styles.buttonRow} style={{ marginTop: 14 }}>
              <div className={styles.buttonGroup}>
                <button
                  className={styles.secondaryButton}
                  onClick={() => onRenameVendor(vendor.id, (renameDrafts[vendor.id] ?? vendor.name).trim())}
                  type="button"
                >
                  Save name
                </button>
                <button className={styles.dangerButton} onClick={() => onDeleteVendor(vendor.id)} type="button">
                  Remove vendor
                </button>
              </div>
              <div className={styles.buttonGroup}>
                <label className={styles.uploadLabel}>
                  <span>{uploadingVendorId === vendor.id ? "Uploading..." : "Upload / Replace document"}</span>
                  <input
                    accept={ACCEPTED_VENDOR_FILES}
                    className={styles.uploadInput}
                    disabled={Boolean(uploadingVendorId)}
                    name={`vendor_document_${vendor.id}`}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      if (!file) {
                        return;
                      }
                      onUploadVendorDocument(vendor.id, file);
                      event.target.value = "";
                    }}
                    type="file"
                  />
                </label>
                <button
                  className={styles.primaryButton}
                  disabled={!vendor.document || Boolean(extractingVendorId)}
                  onClick={() => onExtractVendor(vendor.id)}
                  type="button"
                >
                  {extractingVendorId === vendor.id ? "Extracting..." : "Run extraction"}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ReviewStep({
  vendors,
  reviews,
  selectedVendorId,
  comparisonSettingsDraft,
  isSavingComparison,
  onSelectVendor,
  onChangeComparison,
  onSaveComparison,
  onGoToResults,
}: ReviewStepProps) {
  const reviewsByVendor = useMemo(
    () => new Map(reviews.map((review) => [review.vendor_id, review])),
    [reviews],
  );
  const selectedReview = selectedVendorId ? reviewsByVendor.get(selectedVendorId) ?? null : null;
  const fxRates = comparisonSettingsDraft.fx_rates ?? [];
  const uomOverrides = comparisonSettingsDraft.uom_overrides ?? [];

  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Comparison Settings</h2>
            <p className={styles.cardSubtle}>
              These settings govern cross-currency and cross-UOM comparability before the final commercial run.
            </p>
          </div>
          <div className={styles.buttonGroup}>
            <button className={styles.secondaryButton} onClick={onGoToResults} type="button">
              Go to results
            </button>
            <button className={styles.primaryButton} disabled={isSavingComparison} onClick={onSaveComparison} type="button">
              {isSavingComparison ? "Saving..." : "Save comparison settings"}
            </button>
          </div>
        </div>

        <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
          <label className={styles.label}>
            Base Currency
            <input
              className={styles.input}
              name="base_currency"
              value={comparisonSettingsDraft.base_currency}
              onChange={(event) =>
                onChangeComparison((current) => {
                  current.base_currency = event.target.value.toUpperCase();
                })
              }
            />
          </label>
          <label className={styles.label}>
            FX Effective Date
            <input
              className={styles.input}
              name="fx_effective_date"
              type="date"
              value={comparisonSettingsDraft.fx_effective_date}
              onChange={(event) =>
                onChangeComparison((current) => {
                  current.fx_effective_date = event.target.value;
                })
              }
            />
          </label>
        </div>

        <div className={styles.editorSection}>
          <div className={styles.editorSectionTitle}>FX Rates</div>
          <div className={styles.editorSectionSubtle}>
            Enter only the currencies you need for this session. Live lookup is intentionally out of scope here.
          </div>
          <div className={styles.list}>
            {fxRates.map((rate: FXRate, index: number) => (
              <div className={styles.itemCard} key={`${rate.currency}-${index}`}>
                <div className={`${styles.fieldGrid} ${styles.twoCol}`}>
                  <label className={styles.label}>
                    Currency
                    <input
                      className={styles.input}
                      name={`fx_currency_${index}`}
                      value={rate.currency}
                        onChange={(event) =>
                          onChangeComparison((current) => {
                            current.fx_rates ??= [];
                            current.fx_rates[index].currency = event.target.value.toUpperCase();
                          })
                        }
                    />
                  </label>
                  <label className={styles.label}>
                    Rate To Base
                    <input
                      className={styles.input}
                      name={`fx_rate_to_base_${index}`}
                      type="number"
                      step="0.0001"
                      value={rate.rate_to_base}
                        onChange={(event) =>
                          onChangeComparison((current) => {
                            current.fx_rates ??= [];
                            current.fx_rates[index].rate_to_base = Number(event.target.value || 0);
                          })
                        }
                    />
                  </label>
                </div>
                <div className={styles.buttonGroup} style={{ marginTop: 12 }}>
                  <button
                    className={styles.dangerButton}
                    onClick={() =>
                      onChangeComparison((current) => {
                        current.fx_rates ??= [];
                        current.fx_rates.splice(index, 1);
                      })
                    }
                    type="button"
                  >
                    Remove FX rate
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChangeComparison((current) => {
                current.fx_rates ??= [];
                current.fx_rates.push({
                  currency: "",
                  rate_to_base: 1,
                });
              })
            }
            type="button"
          >
            Add FX rate
          </button>
        </div>

        <div className={styles.editorSection}>
          <div className={styles.editorSectionTitle}>UOM Overrides</div>
          <div className={styles.editorSectionSubtle}>
            Use overrides only when the app cannot deterministically normalize a quoted unit to the RFQ unit.
          </div>
          <div className={styles.list}>
            {uomOverrides.map((override: UomOverride, index: number) => (
              <div className={styles.itemCard} key={`${override.from_uom}-${override.to_uom}-${index}`}>
                <div className={`${styles.fieldGrid} ${styles.threeCol}`}>
                  <label className={styles.label}>
                    From UOM
                    <input
                      className={styles.input}
                      name={`uom_from_${index}`}
                      value={override.from_uom}
                      onChange={(event) =>
                        onChangeComparison((current) => {
                          current.uom_overrides ??= [];
                          current.uom_overrides[index].from_uom = event.target.value;
                        })
                      }
                    />
                  </label>
                  <label className={styles.label}>
                    To UOM
                    <input
                      className={styles.input}
                      name={`uom_to_${index}`}
                      value={override.to_uom}
                      onChange={(event) =>
                        onChangeComparison((current) => {
                          current.uom_overrides ??= [];
                          current.uom_overrides[index].to_uom = event.target.value;
                        })
                      }
                    />
                  </label>
                  <label className={styles.label}>
                    Factor
                    <input
                      className={styles.input}
                      name={`uom_factor_${index}`}
                      type="number"
                      step="0.0001"
                      value={override.factor}
                      onChange={(event) =>
                        onChangeComparison((current) => {
                          current.uom_overrides ??= [];
                          current.uom_overrides[index].factor = Number(event.target.value || 0);
                        })
                      }
                    />
                  </label>
                </div>
                <label className={styles.label} style={{ marginTop: 12 }}>
                  Line Item ID (optional)
                  <input
                    className={styles.input}
                    name={`uom_line_item_id_${index}`}
                    value={override.line_item_id ?? ""}
                    onChange={(event) =>
                      onChangeComparison((current) => {
                        current.uom_overrides ??= [];
                        current.uom_overrides[index].line_item_id = event.target.value || null;
                      })
                    }
                  />
                </label>
                <div className={styles.buttonGroup} style={{ marginTop: 12 }}>
                  <button
                    className={styles.dangerButton}
                    onClick={() =>
                      onChangeComparison((current) => {
                        current.uom_overrides ??= [];
                        current.uom_overrides.splice(index, 1);
                      })
                    }
                    type="button"
                  >
                    Remove override
                  </button>
                </div>
              </div>
            ))}
          </div>
          <button
            className={styles.secondaryButton}
            onClick={() =>
              onChangeComparison((current) => {
                current.uom_overrides ??= [];
                current.uom_overrides.push({
                  from_uom: "",
                  to_uom: "",
                  factor: 1,
                  line_item_id: null,
                });
              })
            }
            type="button"
          >
            Add UOM override
          </button>
        </div>
      </section>

      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Vendor Reviews</h2>
            <p className={styles.cardSubtle}>
              Raw extraction and normalized views remain separate here so the buyer can see what changed.
            </p>
          </div>
        </div>
        <div className={styles.reviewLayout}>
          <div className={styles.reviewSidebar}>
            {vendors.map((vendor) => {
              const review = reviewsByVendor.get(vendor.id);
              return (
                <button
                  className={`${styles.reviewSidebarButton} ${selectedVendorId === vendor.id ? styles.reviewSidebarButtonActive : ""}`}
                  key={vendor.id}
                  onClick={() => onSelectVendor(vendor.id)}
                  type="button"
                >
                  <span>{vendor.name}</span>
                  <span className={`${styles.statusBadge} ${statusClassName(vendor.status)}`}>{vendor.status}</span>
                  <span className={styles.previewItemMeta}>{review ? "Review available" : "No review yet"}</span>
                </button>
              );
            })}
          </div>

          <div className={styles.reviewContent}>
            {!selectedReview ? (
              <div className={`${styles.banner} ${styles.infoBanner}`}>
                Select a vendor with extracted data to inspect its raw and normalized review.
              </div>
            ) : (
              <>
                {selectedReview.visual_fidelity_warning ? (
                  <div className={`${styles.banner} ${styles.infoBanner}`}>
                    {selectedReview.visual_fidelity_warning}
                  </div>
                ) : null}

                {(selectedReview.blockers ?? []).length > 0 ? (
                  <div className={`${styles.banner} ${styles.errorBanner}`}>
                    {(selectedReview.blockers ?? []).join(" ")}
                  </div>
                ) : null}

                {(selectedReview.warnings ?? []).length > 0 ? (
                  <div className={`${styles.banner} ${styles.infoBanner}`}>
                    {(selectedReview.warnings ?? []).join(" ")}
                  </div>
                ) : null}

                <section className={styles.previewPanel}>
                  <div className={styles.previewHeader}>
                    <div>
                      <div className={styles.previewEyebrow}>Raw Extraction</div>
                      <div className={styles.previewTitle}>{selectedReview.document.file_name}</div>
                    </div>
                    <div className={styles.previewBadge}>{formatTimestamp(selectedReview.created_at)}</div>
                  </div>
                  <div className={styles.previewSummary}>{selectedReview.raw_extraction.document_summary}</div>
                  <FieldGroupList title="Question Answers" fields={selectedReview.raw_extraction.question_answers ?? []} />
                  <FieldGroupList title="Schedule Answers" fields={selectedReview.raw_extraction.schedule_answers ?? []} />
                  <FieldGroupList title="Technical Claims" fields={selectedReview.raw_extraction.technical_claims ?? []} />
                  <FieldGroupList title="Commercial Claims" fields={selectedReview.raw_extraction.commercial_claims ?? []} />
                </section>

                <section className={styles.previewPanel}>
                  <div className={styles.previewHeader}>
                    <div>
                      <div className={styles.previewEyebrow}>Normalized View</div>
                      <div className={styles.previewTitle}>Canonical values, comparability, and blockers</div>
                    </div>
                  </div>
                  <NormalizedFieldList fields={selectedReview.normalized_fields ?? []} />
                  <NormalizedPricingTable pricingLines={selectedReview.normalized_pricing ?? []} />
                </section>
              </>
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

export function ResultsStep({
  evaluationReport,
  comparisonSettingsReady,
  isRunningEvaluation,
  onRunEvaluation,
}: ResultsStepProps) {
  return (
    <div className={styles.grid}>
      <section className={styles.card}>
        <div className={styles.cardHeader}>
          <div>
            <h2 className={styles.cardTitle}>Evaluation Run</h2>
            <p className={styles.cardSubtle}>
              Official recommendation uses QCBS 70/30. LCS, QBS, and the AI scenarios are shown only as advisory insights.
            </p>
          </div>
          <div className={styles.buttonGroup}>
            <button
              className={styles.primaryButton}
              disabled={!comparisonSettingsReady || isRunningEvaluation}
              onClick={onRunEvaluation}
              type="button"
            >
              {isRunningEvaluation ? "Running evaluation..." : "Run evaluation"}
            </button>
          </div>
        </div>

        {!comparisonSettingsReady ? (
          <div className={`${styles.banner} ${styles.errorBanner}`}>
            Comparison settings must be saved before the official evaluation can run.
          </div>
        ) : null}
      </section>

      {!evaluationReport ? (
        <div className={`${styles.banner} ${styles.infoBanner}`}>
          No evaluation report is available yet. Run the official evaluation when comparison settings and vendor reviews are ready.
        </div>
      ) : (
        <>
          {(evaluationReport.blocked_reasons ?? []).length > 0 ? (
            <div className={`${styles.banner} ${styles.errorBanner}`}>
              {(evaluationReport.blocked_reasons ?? []).join(" ")}
            </div>
          ) : null}

          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>Official Result</h2>
                <p className={styles.cardSubtle}>
                  This section is the governed output. Everything below under AI insights is advisory only.
                </p>
              </div>
              <div className={`${styles.statusBadge} ${styles.statusBadgeSuccess}`}>Official result</div>
            </div>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Generated At</span>
                <span className={styles.summaryValue}>{formatTimestamp(evaluationReport.generated_at)}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Winner Vendor ID</span>
                <span className={styles.summaryValue}>{evaluationReport.official_recommendation.winner_vendor_id ?? "No winner"}</span>
              </div>
              <div className={styles.summaryItem}>
                <span className={styles.summaryLabel}>Eligible Vendors</span>
                <span className={styles.summaryValue}>
                  {(evaluationReport.official_recommendation.eligible_vendor_ids ?? []).join(", ") || "None"}
                </span>
              </div>
              <div className={styles.summaryNarrative}>
                <span className={styles.summaryLabel}>Explanation</span>
                <span className={styles.summaryValue}>{evaluationReport.official_recommendation.explanation}</span>
              </div>
            </div>
            {(evaluationReport.official_recommendation.risks ?? []).length > 0 ? (
              <div className={styles.summaryNarrative} style={{ marginTop: 16 }}>
                <span className={styles.summaryLabel}>Risks</span>
                <span className={styles.summaryValue}>
                  {(evaluationReport.official_recommendation.risks ?? []).join(" ")}
                </span>
              </div>
            ) : null}
          </section>

          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>Official Score Breakdown</h2>
                <p className={styles.cardSubtle}>
                  Technical is the hard gate. Commercial scoring applies only to the technically qualified pool.
                </p>
              </div>
            </div>
            <div className={styles.tableWrap}>
              <table className={styles.scoreTable}>
                <thead>
                  <tr>
                    <th>Vendor</th>
                    <th>Technical Score</th>
                    <th>Commercial Score</th>
                    <th>Final QCBS Score</th>
                    <th>Passed Technical Gate</th>
                    <th>Commercially Comparable</th>
                  </tr>
                </thead>
                <tbody>
                  {(evaluationReport.official_recommendation.score_breakdown ?? []).map((item) => (
                    <tr key={item.vendor_id}>
                      <td>{item.vendor_name}</td>
                      <td>{formatOptionalNumber(item.technical_score)}</td>
                      <td>{formatOptionalNumber(item.commercial_score)}</td>
                      <td>{formatOptionalNumber(item.final_score)}</td>
                      <td>{item.passed_technical_gate ? "Yes" : "No"}</td>
                      <td>{item.commercially_comparable ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>Technical Evaluation</h2>
                <p className={styles.cardSubtle}>Criterion-level technical outcomes, explanations, and disqualification reasons.</p>
              </div>
            </div>
            <div className={styles.previewList}>
              {(evaluationReport.technical_results ?? []).map((result) => (
                <div className={styles.previewItem} key={result.vendor_id}>
                  <div className={styles.previewItemHeader}>
                    <div className={styles.previewTitle}>{result.vendor_name}</div>
                    <div className={`${styles.statusBadge} ${result.passed_gate ? styles.statusBadgeSuccess : styles.statusBadgeDanger}`}>
                      {result.passed_gate ? "Passed technical gate" : "Failed technical gate"}
                    </div>
                  </div>
                  <div className={styles.previewItemMeta}>
                    Aggregate score: {formatOptionalNumber(result.aggregate_score)} / Threshold {result.threshold}
                  </div>
                  <div className={styles.previewItemBody}>{result.summary}</div>
                  {(result.disqualification_reasons ?? []).length > 0 ? (
                    <div className={styles.previewItemMeta}>
                      Disqualification reasons: {(result.disqualification_reasons ?? []).join(" ")}
                    </div>
                  ) : null}
                  <div className={styles.previewList} style={{ marginTop: 10 }}>
                    {(result.criterion_results ?? []).map((criterion) => (
                      <div className={styles.previewItem} key={criterion.criterion_id}>
                        <div className={styles.previewItemHeader}>
                          <div className={styles.previewItemId}>{criterion.criterion_id}</div>
                          <div className={styles.previewBadge}>
                            {criterion.status}
                            {criterion.score !== null ? ` · ${formatOptionalNumber(criterion.score)}` : ""}
                          </div>
                        </div>
                        <div className={styles.previewTitle}>{criterion.title}</div>
                        <div className={styles.previewItemBody}>{criterion.explanation}</div>
                        <div className={styles.previewItemMeta}>
                          Evidence refs: {(criterion.evidence_refs ?? []).join(", ") || "None"} | Confidence: {formatOptionalNumber(criterion.confidence)}
                        </div>
                        {(criterion.math_trace ?? []).length > 0 ? (
                          <div className={styles.previewItemMeta}>Math trace: {(criterion.math_trace ?? []).join(" ")}</div>
                        ) : null}
                        {(criterion.risks ?? []).length > 0 ? (
                          <div className={styles.previewItemMeta}>Risks: {(criterion.risks ?? []).join(" ")}</div>
                        ) : null}
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>Commercial Evaluation</h2>
                <p className={styles.cardSubtle}>Normalized totals, comparability blockers, pricing anomalies, and commercial scores.</p>
              </div>
            </div>
            <div className={styles.previewList}>
              {(evaluationReport.commercial_results ?? []).map((result) => (
                <div className={styles.previewItem} key={result.vendor_id}>
                  <div className={styles.previewItemHeader}>
                    <div className={styles.previewTitle}>{result.vendor_name}</div>
                    <div className={`${styles.statusBadge} ${result.award_ready ? styles.statusBadgeSuccess : styles.statusBadgeWarning}`}>
                      {result.award_ready ? "Award-ready" : "Blocked"}
                    </div>
                  </div>
                  <div className={styles.previewItemMeta}>
                    Comparable total: {formatOptionalNumber(result.comparable_total)} {result.base_currency}
                    {result.commercial_score !== null ? ` · Commercial score ${formatOptionalNumber(result.commercial_score)}` : ""}
                  </div>
                  <div className={styles.previewItemBody}>{result.explanation}</div>
                  {(result.blockers ?? []).length > 0 ? (
                    <div className={styles.previewItemMeta}>Blockers: {(result.blockers ?? []).join(" ")}</div>
                  ) : null}
                  {(result.anomalies ?? []).length > 0 ? (
                    <div className={styles.previewItemMeta}>Anomalies: {(result.anomalies ?? []).join(" ")}</div>
                  ) : null}
                </div>
              ))}
            </div>
          </section>

          <section className={styles.card}>
            <div className={styles.cardHeader}>
              <div>
                <h2 className={styles.cardTitle}>AI Insights</h2>
                <p className={styles.cardSubtle}>These scenarios are advisory only. They never override the official QCBS recommendation.</p>
              </div>
              <div className={`${styles.statusBadge} ${styles.statusBadgeWarning}`}>AI insights</div>
            </div>
            <div className={styles.previewList}>
              {(evaluationReport.advisory_scenarios ?? []).map((scenario, index) => (
                <div className={styles.previewItem} key={`${scenario.scenario_name}-${index}`}>
                  <div className={styles.previewItemHeader}>
                    <div>
                      <div className={styles.previewTitle}>{scenario.scenario_name}</div>
                      <div className={styles.previewItemMeta}>{scenario.scenario_kind}</div>
                    </div>
                    <div className={styles.previewBadge}>Winner: {scenario.winner_vendor_id ?? "None"}</div>
                  </div>
                  <div className={styles.previewItemBody}>{scenario.explanation}</div>
                  <div className={styles.previewItemMeta}>{scenario.weighting_or_rule_basis}</div>
                  {(scenario.excluded_vendor_ids ?? []).length > 0 ? (
                    <div className={styles.previewItemMeta}>
                      Excluded vendors: {(scenario.excluded_vendor_ids ?? []).join(", ")}
                    </div>
                  ) : null}
                  <div className={styles.tableWrap}>
                    <table className={styles.scoreTable}>
                      <thead>
                        <tr>
                          <th>Vendor</th>
                          <th>Score</th>
                          <th>Notes</th>
                        </tr>
                      </thead>
                      <tbody>
                        {(scenario.ranking ?? []).map((item) => (
                          <tr key={`${scenario.scenario_name}-${item.vendor_id}`}>
                            <td>{item.vendor_name}</td>
                            <td>{formatOptionalNumber(item.score)}</td>
                            <td>{(item.notes ?? []).join(" ") || "None"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function FieldGroupList({ title, fields }: { title: string; fields: ExtractedField[] }) {
  return (
    <div className={styles.previewSection}>
      <div className={styles.previewSectionTitle}>{title}</div>
      {fields.length === 0 ? (
        <div className={styles.previewEmpty}>No fields captured.</div>
      ) : (
        <div className={styles.previewList}>
          {fields.map((field) => (
            <div className={styles.previewItem} key={field.id}>
              <div className={styles.previewItemHeader}>
                <div className={styles.previewItemId}>{field.id}</div>
                <div className={styles.previewBadge}>{field.state}</div>
              </div>
              <div className={styles.previewTitle}>{field.label}</div>
              <div className={styles.previewItemBody}>{field.raw_value ?? "No raw value extracted."}</div>
              <div className={styles.previewItemMeta}>
                Question: {field.question_id ?? "None"} | Schedule: {field.schedule_id ?? "None"} | Line item: {field.line_item_id ?? "None"}
              </div>
              <div className={styles.previewItemMeta}>
                Currency: {field.currency ?? "N/A"} | UOM: {field.uom ?? "N/A"} | Numeric: {formatOptionalNumber(field.numeric_value)}
              </div>
              {field.notes ? <div className={styles.previewItemMeta}>Notes: {field.notes}</div> : null}
              <div className={styles.previewItemMeta}>
                Evidence: {(field.evidence ?? []).map((anchor) => `${anchor.locator}: ${anchor.snippet}`).join(" | ") || "None"}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NormalizedFieldList({ fields }: { fields: NormalizedField[] }) {
  return (
    <div className={styles.previewSection}>
      <div className={styles.previewSectionTitle}>Normalized Fields</div>
      {fields.length === 0 ? (
        <div className={styles.previewEmpty}>No normalized fields are available.</div>
      ) : (
        <div className={styles.previewList}>
          {fields.map((field) => (
            <div className={styles.previewItem} key={field.id}>
              <div className={styles.previewItemHeader}>
                <div className={styles.previewItemId}>{field.id}</div>
                <div className={styles.previewBadge}>{field.comparability_status}</div>
              </div>
              <div className={styles.previewTitle}>{field.label}</div>
              <div className={styles.previewItemBody}>{field.normalized_value ?? "No normalized value"}</div>
              <div className={styles.previewItemMeta}>
                Base currency value: {formatOptionalNumber(field.base_currency_value)} | Target UOM: {field.target_uom ?? "N/A"}
              </div>
              {(field.conversion_notes ?? []).length > 0 ? (
                <div className={styles.previewItemMeta}>Conversion notes: {(field.conversion_notes ?? []).join(" ")}</div>
              ) : null}
              {(field.blockers ?? []).length > 0 ? (
                <div className={styles.previewItemMeta}>Blockers: {(field.blockers ?? []).join(" ")}</div>
              ) : null}
              <div className={styles.previewItemMeta}>Evidence refs: {(field.evidence_refs ?? []).join(", ") || "None"}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function NormalizedPricingTable({ pricingLines }: { pricingLines: NormalizedPricingLine[] }) {
  return (
    <div className={styles.previewSection}>
      <div className={styles.previewSectionTitle}>Normalized Pricing</div>
      <div className={styles.tableWrap}>
        <table className={styles.scoreTable}>
          <thead>
            <tr>
              <th>Line Item</th>
              <th>Total Price</th>
              <th>Base Currency Total</th>
              <th>Quoted UOM</th>
              <th>Target UOM</th>
              <th>Comparability</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {pricingLines.map((line) => (
              <tr key={line.line_item_id}>
                <td>{line.line_item_name}</td>
                <td>
                  {formatOptionalNumber(line.total_price)} {line.currency ?? ""}
                </td>
                <td>{formatOptionalNumber(line.base_currency_total)}</td>
                <td>{line.uom ?? "N/A"}</td>
                <td>{line.target_uom ?? "N/A"}</td>
                <td>{line.comparability_status}</td>
                <td>
              {[...(line.exclusions ?? []), ...(line.conversion_notes ?? []), ...(line.blockers ?? [])].join(" ") || "None"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatOptionalNumber(value: number | null | undefined): string {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return "N/A";
  }
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatTimestamp(value?: string | null): string {
  if (!value) {
    return "Not available";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function statusClassName(status: string): string {
  if (status === "evaluated" || status === "evaluation_ready") {
    return styles.statusBadgeSuccess;
  }
  if (status === "uploaded" || status === "extracted") {
    return styles.statusBadgeWarning;
  }
  return styles.statusBadgeNeutral;
}
