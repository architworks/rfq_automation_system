"use client";

import { useEffect, useMemo, useState } from "react";

import type {
    CommercialEvaluationResult,
    Criterion,
    ComparisonSettings,
    ExtractedField,
    EvaluationReport,
    LockedFrameworkArtifact,
    NormalizedField,
    NormalizedPricingLine,
    Question,
    TechnicalEvaluationResult,
    TechnicalCriterionResult,
    VendorPack,
    VendorRecord,
    VendorReview,
} from "@/lib/api";
import { FormInput } from "./form-fields";
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
  isExtractingVendors: boolean;
  onCreateVendor: (name: string) => void;
  onRenameVendor: (vendorId: string, name: string) => void;
  onDeleteVendor: (vendorId: string) => void;
  onUploadVendorDocument: (vendorId: string, file: File) => void;
  onExtractUploadedVendors: () => void;
  onGoToReview: () => void;
};

type ReviewStepProps = {
  artifact: LockedFrameworkArtifact | null;
  evaluationReport: EvaluationReport | null;
  vendors: VendorRecord[];
  reviews: VendorReview[];
  selectedVendorId: string | null;
  comparisonSettings: ComparisonSettings | null;
  onSelectVendor: (vendorId: string) => void;
  onGoToResults: () => void;
};

type ResultsStepProps = {
  artifact: LockedFrameworkArtifact | null;
  comparisonSettings: ComparisonSettings | null;
  evaluationReport: EvaluationReport | null;
  normalizationReady: boolean;
  isRunningEvaluation: boolean;
  onRunEvaluation: () => void;
  reviews: VendorReview[];
};

type VendorScoreBreakdownItem = NonNullable<
  NonNullable<EvaluationReport["official_recommendation"]["score_breakdown"]>[number]
>;

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
            <h2 className={styles.cardTitle}>Vendor RFQ Pack Preview</h2>
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
  isExtractingVendors,
  onCreateVendor,
  onRenameVendor,
  onDeleteVendor,
  onUploadVendorDocument,
  onExtractUploadedVendors,
  onGoToReview,
}: VendorsStepProps) {
  const [newVendorName, setNewVendorName] = useState("");
  const [renameDrafts, setRenameDrafts] = useState<Record<string, string>>({});
  const pendingExtractionCount = vendors.filter(
    (vendor) => vendor.document && vendor.status === "uploaded",
  ).length;

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
            <h2 className={styles.cardTitle}>Add Vendors</h2>
            <p className={styles.cardSubtle}>
              Register vendors here. Upload all source documents first, then run one extraction job for every uploaded vendor.
            </p>
            <p className={styles.cardSubtle}>One document per vendor. Native file input is used for PDF, Word, PowerPoint, and Excel uploads.</p>
          </div>
        </div>
        <div className={styles.vendorToolbar}>
          <FormInput
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
          <button
            className={styles.primaryButton}
            disabled={pendingExtractionCount === 0 || Boolean(uploadingVendorId) || isExtractingVendors}
            onClick={onExtractUploadedVendors}
            type="button"
          >
            {isExtractingVendors
              ? "Extracting uploaded vendors..."
              : pendingExtractionCount > 0
                ? `Extract all uploaded vendors (${pendingExtractionCount})`
                : "Extract all uploaded vendors"}
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
                <FormInput
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
                  <FormInput
                    accept={ACCEPTED_VENDOR_FILES}
                    className={styles.uploadInput}
                    disabled={Boolean(uploadingVendorId) || isExtractingVendors}
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
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ReviewStep({
  artifact,
  evaluationReport,
  vendors,
  reviews,
  selectedVendorId,
  comparisonSettings,
  onSelectVendor,
  onGoToResults,
}: ReviewStepProps) {
  const reviewsByVendor = useMemo(
    () => new Map(reviews.map((review) => [review.vendor_id, review])),
    [reviews],
  );
  const selectedReview = selectedVendorId ? reviewsByVendor.get(selectedVendorId) ?? null : null;
  const questionsById = useMemo(
    () => new Map((artifact?.rubric_snapshot.questions ?? []).map((question) => [question.id, question])),
    [artifact],
  );
  const criteriaByQuestionId = useMemo(() => {
    const lookup = new Map<string, Criterion>();
    for (const criterion of artifact?.rubric_snapshot.criteria ?? []) {
      for (const questionId of criterion.linked_question_ids ?? []) {
        if (questionId) {
          lookup.set(questionId, criterion);
        }
      }
    }
    return lookup;
  }, [artifact]);
  const selectedTechnicalResult = useMemo(
    () => (selectedVendorId ? (evaluationReport?.technical_results ?? []).find((item) => item.vendor_id === selectedVendorId) ?? null : null),
    [evaluationReport, selectedVendorId],
  );
  const selectedVendor = useMemo(
    () => (selectedVendorId ? vendors.find((vendor) => vendor.id === selectedVendorId) ?? null : null),
    [selectedVendorId, vendors],
  );
  const criterionResultsById = useMemo(
    () => new Map((selectedTechnicalResult?.criterion_results ?? []).map((criterion) => [criterion.criterion_id, criterion])),
    [selectedTechnicalResult],
  );
  const reviewSections = useMemo(
    () => [
      { id: "review-document-summary", label: "Summary" },
      { id: "review-question-answers", label: "Question Answers" },
      { id: "review-schedule-answers", label: "Schedule Answers" },
      { id: "review-technical-claims", label: "Technical Claims" },
      { id: "review-commercial-notes", label: "Commercial Notes" },
      { id: "review-normalized-fields", label: "Normalized Fields" },
      { id: "review-normalized-pricing", label: "Normalized Pricing" },
    ],
    [],
  );

  return (
    <div className={styles.reviewPageLayout}>
      <aside className={styles.reviewPageSidebar}>
        <div className={styles.reviewSectionDock}>
          <div className={styles.previewSectionTitle}>Review Navigation</div>
          {selectedReview && selectedVendor ? (
            <>
              <div className={styles.previewItemMeta}>
                Jump across the extracted sections for <strong>{selectedVendor.name}</strong>.
              </div>
              <div className={styles.reviewSectionNavList}>
                {reviewSections.map((section) => (
                  <button
                    className={styles.reviewSectionNavButton}
                    key={section.id}
                    onClick={() => scrollToReviewSection(section.id)}
                    type="button"
                  >
                    {section.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className={styles.reviewSectionDockEmpty}>
              Select a vendor with extracted data to enable section navigation.
            </div>
          )}
        </div>
      </aside>

      <div className={styles.reviewPageMain}>
        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>Normalization Basis</h2>
              <p className={styles.cardSubtle}>
                Commercial normalization is automatic. The RFQ base currency drives FX conversion, and only weight or volume UOMs convert mathematically.
              </p>
            </div>
            <div className={styles.buttonGroup}>
              <button className={styles.secondaryButton} onClick={onGoToResults} type="button">
                Go to results
              </button>
            </div>
          </div>

          <div className={styles.summaryGrid}>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>RFQ Currency</span>
              <span className={styles.summaryValue}>{comparisonSettings?.base_currency ?? "Not available"}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>FX Effective Date</span>
              <span className={styles.summaryValue}>{comparisonSettings?.fx_effective_date ?? "Not available"}</span>
            </div>
            <div className={styles.summaryItem}>
              <span className={styles.summaryLabel}>FX Coverage</span>
              <span className={styles.summaryValue}>
                {comparisonSettings ? `${(comparisonSettings.fx_rates ?? []).length + 1} currencies` : "Not available"}
              </span>
            </div>
            <div className={styles.summaryNarrative}>
              <span className={styles.summaryLabel}>Normalization Policy</span>
              <span className={styles.summaryValue}>
                Currency conversion uses the stored ECB snapshot. Lot and Count do not convert. Only weight and volume units convert mathematically.
              </span>
            </div>
          </div>
        </section>

        <section className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>Extraction Review</h2>
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

                  <div className={styles.reviewSectionContent}>
                    <section className={styles.previewPanel}>
                      <div className={styles.previewHeader}>
                        <div>
                          <div className={styles.previewEyebrow}>Raw Extraction</div>
                          <div className={styles.previewTitle}>{selectedReview.document.file_name}</div>
                        </div>
                        <div className={styles.previewBadge}>{formatTimestamp(selectedReview.created_at)}</div>
                      </div>
                      <div className={styles.summaryNarrative} id="review-document-summary">
                        <span className={styles.summaryLabel}>Document Summary</span>
                        <span className={styles.summaryValue}>{selectedReview.raw_extraction.document_summary}</span>
                      </div>
                      <QuestionAnswerList
                        criterionResultsById={criterionResultsById}
                        criteriaByQuestionId={criteriaByQuestionId}
                        fields={selectedReview.raw_extraction.question_answers ?? []}
                        questionLookup={questionsById}
                      />
                      <FieldGroupList
                        sectionId="review-schedule-answers"
                        title="Schedule Answers"
                        fields={selectedReview.raw_extraction.schedule_answers ?? []}
                      />
                      <FieldGroupList
                        sectionId="review-technical-claims"
                        title="Technical Claims"
                        fields={selectedReview.raw_extraction.technical_claims ?? []}
                      />
                      <FieldGroupList
                        sectionId="review-commercial-notes"
                        title="Commercial Notes / Anomalies"
                        fields={selectedReview.raw_extraction.commercial_claims ?? []}
                      />
                    </section>

                    <section className={styles.previewPanel}>
                      <div className={styles.previewHeader}>
                        <div>
                          <div className={styles.previewEyebrow}>Normalized View</div>
                          <div className={styles.previewTitle}>Canonical values, comparability, and blockers</div>
                        </div>
                      </div>
                      <NormalizedFieldList
                        fields={selectedReview.normalized_fields ?? []}
                        rfqCurrency={comparisonSettings?.base_currency ?? null}
                        sectionId="review-normalized-fields"
                      />
                      <NormalizedPricingTable
                        pricingLines={selectedReview.normalized_pricing ?? []}
                        rfqCurrency={comparisonSettings?.base_currency ?? null}
                        sectionId="review-normalized-pricing"
                      />
                    </section>
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

export function ResultsStep({
  artifact,
  comparisonSettings,
  evaluationReport,
  normalizationReady,
  isRunningEvaluation,
  onRunEvaluation,
  reviews,
}: ResultsStepProps) {
  const criteriaById = useMemo(
    () => new Map((artifact?.rubric_snapshot.criteria ?? []).map((criterion) => [criterion.id, criterion])),
    [artifact],
  );
  const questionsById = useMemo(
    () => new Map((artifact?.rubric_snapshot.questions ?? []).map((question) => [question.id, question])),
    [artifact],
  );
  const evidenceLookupByVendor = useMemo(
    () =>
      new Map(
        reviews.map((review) => [review.vendor_id, buildEvidenceLookup(review)]),
      ),
    [reviews],
  );
  const technicalResultsByVendor = useMemo(
    () =>
      new Map(
        (evaluationReport?.technical_results ?? []).map((result) => [result.vendor_id, result]),
      ),
    [evaluationReport],
  );
  const commercialResultsByVendor = useMemo(
    () =>
      new Map(
        (evaluationReport?.commercial_results ?? []).map((result) => [result.vendor_id, result]),
      ),
    [evaluationReport],
  );
  const rankedScoreBreakdown = useMemo(
    () =>
      rankVendorBreakdowns(
        evaluationReport?.official_recommendation.score_breakdown ?? [],
        evaluationReport?.official_recommendation.winner_vendor_id ?? null,
      ),
    [evaluationReport],
  );
  const scoreBreakdownByVendor = useMemo(
    () =>
      new Map(
        rankedScoreBreakdown.map((item) => [item.vendor_id, item]),
      ),
    [rankedScoreBreakdown],
  );
  const technicalThreshold = evaluationReport?.technical_results?.[0]?.threshold ?? null;
  const winnerBreakdown =
    (evaluationReport?.official_recommendation.winner_vendor_id
      ? scoreBreakdownByVendor.get(evaluationReport.official_recommendation.winner_vendor_id)
      : null) ?? null;
  const winnerName =
    winnerBreakdown?.vendor_name ??
    evaluationReport?.official_recommendation.winner_vendor_id ??
    "No winner";
  const eligibleVendorNames = useMemo(
    () =>
      (evaluationReport?.official_recommendation.eligible_vendor_ids ?? []).map(
        (vendorId) => scoreBreakdownByVendor.get(vendorId)?.vendor_name ?? vendorId,
      ),
    [evaluationReport, scoreBreakdownByVendor],
  );
  const podiumEntries = useMemo(
    () =>
      buildPodiumEntries(
        rankedScoreBreakdown,
        evaluationReport?.official_recommendation.winner_vendor_id ?? null,
      ),
    [evaluationReport, rankedScoreBreakdown],
  );
  const resultsSections = useMemo(
    () => [
      { id: "results-official-result", label: "Official Award" },
      { id: "results-ai-insights", label: "AI Insights" },
      { id: "results-score-breakdown", label: "Score Trace" },
      { id: "results-technical-evaluation", label: "Technical Detail" },
      { id: "results-commercial-evaluation", label: "Commercial Detail" },
    ],
    [],
  );

  return (
    <div className={styles.reviewPageLayout}>
      <aside className={styles.reviewPageSidebar}>
        <div className={styles.reviewSectionDock}>
          <div className={styles.previewSectionTitle}>Results Navigation</div>
          {evaluationReport ? (
            <>
              <div className={styles.previewItemMeta}>
                Jump between the official award, score trace, and advisory sections without losing your place.
              </div>
              <div className={styles.reviewSectionNavList}>
                {resultsSections.map((section) => (
                  <button
                    className={styles.reviewSectionNavButton}
                    key={section.id}
                    onClick={() => scrollToReviewSection(section.id)}
                    type="button"
                  >
                    {section.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <div className={styles.reviewSectionDockEmpty}>
              Run the evaluation to unlock section navigation for the official result and score trace.
            </div>
          )}
        </div>
      </aside>

      <div className={styles.reviewPageMain}>
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
                disabled={!normalizationReady || isRunningEvaluation}
                onClick={onRunEvaluation}
                type="button"
              >
                {isRunningEvaluation ? "Running evaluation..." : "Run evaluation"}
              </button>
            </div>
          </div>

          {!normalizationReady ? (
            <div className={`${styles.banner} ${styles.errorBanner}`}>
              Automatic normalization basis is unavailable. Set a supported RFQ currency and lock the framework again.
            </div>
          ) : null}
        </section>

        {!evaluationReport ? (
          <div className={`${styles.banner} ${styles.infoBanner}`}>
            No evaluation report is available yet. Run the official evaluation when vendor reviews and automatic normalization are ready.
          </div>
        ) : (
          <>
            {(evaluationReport.blocked_reasons ?? []).length > 0 ? (
              <div className={`${styles.banner} ${styles.errorBanner}`}>
                {(evaluationReport.blocked_reasons ?? []).join(" ")}
              </div>
            ) : null}

            <section className={styles.card} id="results-official-result">
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>Official Result</h2>
                  <p className={styles.cardSubtle}>
                    This is the governed QCBS 70/30 award outcome. AI insights remain advisory and are shown separately.
                  </p>
                </div>
                <div className={`${styles.statusBadge} ${styles.statusBadgeSuccess}`}>Official result</div>
              </div>

              <div className={styles.resultsHeroLayout}>
                <div className={styles.winnerHero}>
                  <div className={styles.winnerHeroEyebrow}>Official QCBS 70/30 Winner</div>
                  <div className={styles.winnerHeroName}>{winnerName}</div>
                  <div className={styles.winnerHeroSummary}>
                    {evaluationReport.official_recommendation.explanation}
                  </div>
                  <div className={styles.winnerMetricGrid}>
                    <div className={styles.winnerMetricCard}>
                      <span className={styles.winnerMetricLabel}>Final QCBS Score</span>
                      <span className={styles.winnerMetricValue}>
                        {formatOptionalNumber(winnerBreakdown?.final_score)}
                      </span>
                    </div>
                    <div className={styles.winnerMetricCard}>
                      <span className={styles.winnerMetricLabel}>Technical Score</span>
                      <span className={styles.winnerMetricValue}>
                        {formatOptionalNumber(winnerBreakdown?.technical_score)}
                      </span>
                    </div>
                    <div className={styles.winnerMetricCard}>
                      <span className={styles.winnerMetricLabel}>Commercial Score</span>
                      <span className={styles.winnerMetricValue}>
                        {formatOptionalNumber(winnerBreakdown?.commercial_score)}
                      </span>
                    </div>
                  </div>
                </div>

                <div className={styles.podiumGrid}>
                  {podiumEntries.length > 0 ? (
                    podiumEntries.map((item, index) => (
                      <div
                        className={`${styles.podiumCard} ${index === 0 ? styles.podiumCardWinner : ""}`}
                        key={item.vendor_id}
                      >
                        <div className={styles.podiumRank}>#{index + 1}</div>
                        <div className={styles.podiumVendor}>{item.vendor_name}</div>
                        <div className={styles.podiumScore}>
                          {formatOptionalNumber(item.final_score)}
                        </div>
                        <div className={styles.podiumMeta}>
                          {item.passed_technical_gate ? "Passed technical gate" : "Failed technical gate"}
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className={styles.podiumEmpty}>
                      No ranked score breakdown is available yet.
                    </div>
                  )}
                </div>
              </div>

              <div className={styles.summaryGrid} style={{ marginTop: 18 }}>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Generated At</span>
                  <span className={styles.summaryValue}>{formatTimestamp(evaluationReport.generated_at)}</span>
                </div>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Eligible Vendors</span>
                  <span className={styles.summaryValue}>
                    {eligibleVendorNames.join(", ") || "None"}
                  </span>
                </div>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Framework Technical Threshold</span>
                  <span className={styles.summaryValue}>
                    {technicalThreshold !== null ? `${formatOptionalNumber(technicalThreshold)} / 100` : "Not available"}
                  </span>
                </div>
                <div className={styles.summaryItem}>
                  <span className={styles.summaryLabel}>Commercial Comparison Currency</span>
                  <span className={styles.summaryValue}>{comparisonSettings?.base_currency ?? "Not available"}</span>
                </div>
              </div>

              {(evaluationReport.official_recommendation.risks ?? []).length > 0 ? (
                <div className={styles.reviewInsightBox} style={{ marginTop: 16 }}>
                  <span className={styles.summaryLabel}>Decision Risks</span>
                  <span className={styles.summaryValue}>
                    {(evaluationReport.official_recommendation.risks ?? []).join(" ")}
                  </span>
                </div>
              ) : null}
            </section>

            <section className={styles.card} id="results-ai-insights">
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>AI Insights</h2>
                  <p className={styles.cardSubtle}>
                    These scenarios are advisory only. They never override the official QCBS recommendation.
                  </p>
                </div>
                <div className={`${styles.statusBadge} ${styles.statusBadgeWarning}`}>AI insights</div>
              </div>
              {(evaluationReport.advisory_scenarios ?? []).length === 0 ? (
                <div className={styles.previewEmpty}>No advisory AI scenarios are available.</div>
              ) : (
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
              )}
            </section>

            <section className={styles.card} id="results-score-breakdown">
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>Official Score Breakdown</h2>
                  <p className={styles.cardSubtle}>
                    Technical is the hard gate. Vendors must clear mandatory gates, criterion-level cutoffs, and the
                    framework technical threshold before commercial scoring applies.
                  </p>
                </div>
              </div>
              <div className={styles.frameworkNote}>
                Framework technical threshold:{" "}
                {technicalThreshold !== null ? `${formatOptionalNumber(technicalThreshold)} / 100` : "Not available"}.
                Expand a vendor below to trace the exact technical and commercial numbers behind its result.
              </div>
              <div className={styles.tableWrap}>
                <table className={styles.scoreTable}>
                  <thead>
                    <tr>
                      <th>Vendor</th>
                      <th>Technical Gate</th>
                      <th>Technical Score</th>
                      <th>Commercial Status</th>
                      <th>Commercial Score</th>
                      <th>Final QCBS Score</th>
                      <th>Award Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankedScoreBreakdown.map((item) => (
                      <tr
                        className={
                          item.vendor_id === evaluationReport.official_recommendation.winner_vendor_id
                            ? styles.scoreRowWinner
                            : undefined
                        }
                        key={item.vendor_id}
                      >
                        <td>{item.vendor_name}</td>
                        <td>{item.passed_technical_gate ? "Passed" : "Failed"}</td>
                        <td>{formatOptionalNumber(item.technical_score)}</td>
                        <td>{item.commercially_comparable ? "Comparable" : "Blocked / Not comparable"}</td>
                        <td>{formatOptionalNumber(item.commercial_score)}</td>
                        <td>{formatOptionalNumber(item.final_score)}</td>
                        <td>
                          {item.vendor_id === evaluationReport.official_recommendation.winner_vendor_id
                            ? "Official winner"
                            : item.passed_technical_gate
                              ? "Ranked"
                              : "Stopped at technical gate"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className={styles.scoreTraceList}>
                {rankedScoreBreakdown.map((item) => (
                  <OfficialScoreTraceCard
                    commercialResult={commercialResultsByVendor.get(item.vendor_id) ?? null}
                    criteriaById={criteriaById}
                    key={item.vendor_id}
                    scoreBreakdown={item}
                    technicalResult={technicalResultsByVendor.get(item.vendor_id) ?? null}
                    technicalThreshold={technicalThreshold}
                    winnerVendorId={evaluationReport.official_recommendation.winner_vendor_id ?? null}
                  />
                ))}
              </div>
            </section>

            <section className={styles.card} id="results-technical-evaluation">
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>Technical Evaluation</h2>
                  <p className={styles.cardSubtle}>
                    Expand a vendor to inspect the criterion-by-criterion technical evaluation and supporting evidence.
                  </p>
                </div>
              </div>
              <div className={styles.previewList}>
                {(evaluationReport.technical_results ?? []).map((result) => (
                  <details className={styles.resultAccordion} key={result.vendor_id}>
                    <summary className={styles.resultAccordionSummary}>
                      <div className={styles.resultAccordionHeader}>
                        <div>
                          <div className={styles.resultAccordionTitle}>{result.vendor_name}</div>
                          <div className={styles.resultAccordionMeta}>
                            {result.passed_gate ? "Qualified for commercial evaluation" : "Stopped at technical evaluation"}
                          </div>
                        </div>
                        <div className={styles.resultAccordionSummaryMetrics}>
                          <div className={styles.resultMetricPill}>
                            <span className={styles.resultMetricLabel}>Technical Score</span>
                            <strong className={styles.resultMetricValue}>
                              {formatOptionalNumber(result.aggregate_score)} / 100
                            </strong>
                          </div>
                          <div
                            className={`${styles.statusBadge} ${
                              result.passed_gate ? styles.statusBadgeSuccess : styles.statusBadgeDanger
                            }`}
                          >
                            {result.passed_gate ? "Passed technical gate" : "Failed technical gate"}
                          </div>
                        </div>
                      </div>
                    </summary>

                    <div className={styles.resultAccordionBody}>
                      <div className={styles.summaryGrid}>
                        <div className={styles.summaryItem}>
                          <span className={styles.summaryLabel}>Aggregate Technical Score</span>
                          <span className={styles.summaryValue}>{formatOptionalNumber(result.aggregate_score)} / 100</span>
                        </div>
                        <div className={styles.summaryItem}>
                          <span className={styles.summaryLabel}>Technical Gate Result</span>
                          <span className={styles.summaryValue}>
                            {result.passed_gate ? "Qualified for commercial evaluation" : "Stopped at technical evaluation"}
                          </span>
                        </div>
                      </div>

                      <div className={styles.frameworkNote}>
                        Framework technical threshold: {formatOptionalNumber(result.threshold)} / 100.
                      </div>

                      <div className={styles.summaryNarrative}>
                        <span className={styles.summaryLabel}>Technical Evaluation Summary</span>
                        <span className={styles.summaryValue}>{result.summary}</span>
                      </div>

                      {(result.disqualification_reasons ?? []).length > 0 ? (
                        <div className={styles.reviewInsightBox}>
                          <span className={styles.summaryLabel}>Why This Vendor Did Not Pass</span>
                          <span className={styles.summaryValue}>
                            {(result.disqualification_reasons ?? []).join(" ")}
                          </span>
                        </div>
                      ) : null}

                      <div className={styles.previewList}>
                        {(result.criterion_results ?? []).map((criterion) => (
                          <TechnicalCriterionCard
                            criterionDefinition={criteriaById.get(criterion.criterion_id) ?? null}
                            evidenceLookup={evidenceLookupByVendor.get(result.vendor_id) ?? new Map<string, string>()}
                            key={criterion.criterion_id}
                            questionLookup={questionsById}
                            result={criterion}
                          />
                        ))}
                      </div>
                    </div>
                  </details>
                ))}
              </div>
            </section>

            <section className={styles.card} id="results-commercial-evaluation">
              <div className={styles.cardHeader}>
                <div>
                  <h2 className={styles.cardTitle}>Commercial Evaluation</h2>
                  <p className={styles.cardSubtle}>
                    Expand a vendor to inspect normalized totals, pricing blockers, line-item comparison status, and commercial scoring.
                  </p>
                </div>
              </div>
              <div className={styles.previewList}>
                {(evaluationReport.commercial_results ?? []).map((result) => (
                  <details className={styles.resultAccordion} key={result.vendor_id}>
                    <summary className={styles.resultAccordionSummary}>
                      <div className={styles.resultAccordionHeader}>
                        <div>
                          <div className={styles.resultAccordionTitle}>{result.vendor_name}</div>
                          <div className={styles.resultAccordionMeta}>
                            {result.award_ready ? "Commercially comparable and award-ready" : "Commercial comparison blocked"}
                          </div>
                        </div>
                        <div className={styles.resultAccordionSummaryMetrics}>
                          <div className={styles.resultMetricPill}>
                            <span className={styles.resultMetricLabel}>Normalized Total</span>
                            <strong className={styles.resultMetricValue}>
                              {formatOptionalNumber(result.comparable_total)} {result.base_currency}
                            </strong>
                          </div>
                          <div className={styles.resultMetricPill}>
                            <span className={styles.resultMetricLabel}>Commercial Score</span>
                            <strong className={styles.resultMetricValue}>
                              {formatOptionalNumber(result.commercial_score)}
                            </strong>
                          </div>
                        </div>
                      </div>
                    </summary>

                    <div className={styles.resultAccordionBody}>
                      <div className={styles.summaryGrid}>
                        <div className={styles.summaryItem}>
                          <span className={styles.summaryLabel}>Normalized Total In RFQ Currency</span>
                          <span className={styles.summaryValue}>
                            {formatOptionalNumber(result.comparable_total)} {result.base_currency}
                          </span>
                        </div>
                        <div className={styles.summaryItem}>
                          <span className={styles.summaryLabel}>Commercial Score</span>
                          <span className={styles.summaryValue}>{formatOptionalNumber(result.commercial_score)}</span>
                        </div>
                        <div className={styles.summaryItem}>
                          <span className={styles.summaryLabel}>Commercial Status</span>
                          <span className={styles.summaryValue}>
                            {result.award_ready ? "Comparable and award-ready" : "Blocked / not comparable"}
                          </span>
                        </div>
                      </div>

                      <div className={styles.summaryNarrative}>
                        <span className={styles.summaryLabel}>Commercial Evaluation Summary</span>
                        <span className={styles.summaryValue}>{result.explanation}</span>
                      </div>

                      {(result.line_items ?? []).length > 0 ? (
                        <div className={styles.traceSection}>
                          <div className={styles.traceSectionTitle}>Line-item commercial trace</div>
                          <div className={styles.tableWrap}>
                            <table className={styles.scoreTable}>
                              <thead>
                                <tr>
                                  <th>Line Item</th>
                                  <th>Normalized Total</th>
                                  <th>Comparison Status</th>
                                  <th>Notes</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(result.line_items ?? []).map((lineItem) => (
                                  <tr key={`${result.vendor_id}-${lineItem.line_item_id}`}>
                                    <td>{lineItem.line_item_name}</td>
                                    <td>
                                      {formatOptionalNumber(lineItem.base_currency_total)} {result.base_currency}
                                    </td>
                                    <td>{formatComparabilityStatus(lineItem.comparability_status)}</td>
                                    <td>{(lineItem.notes ?? []).join(" ") || "None"}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      ) : null}

                      {(result.blockers ?? []).length > 0 ? (
                        <div className={styles.reviewInsightBox}>
                          <span className={styles.summaryLabel}>Commercial Blockers</span>
                          <span className={styles.summaryValue}>{(result.blockers ?? []).join(" ")}</span>
                        </div>
                      ) : null}

                      {(result.anomalies ?? []).length > 0 ? (
                        <div className={styles.reviewInsightBox}>
                          <span className={styles.summaryLabel}>Commercial Anomalies</span>
                          <span className={styles.summaryValue}>{(result.anomalies ?? []).join(" ")}</span>
                        </div>
                      ) : null}
                    </div>
                  </details>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function OfficialScoreTraceCard({
  commercialResult,
  criteriaById,
  scoreBreakdown,
  technicalResult,
  technicalThreshold,
  winnerVendorId,
}: {
  commercialResult: CommercialEvaluationResult | null;
  criteriaById: Map<string, Criterion>;
  scoreBreakdown: VendorScoreBreakdownItem;
  technicalResult: TechnicalEvaluationResult | null;
  technicalThreshold: number | null;
  winnerVendorId: string | null;
}) {
  const failedTechnicalCriteria = (technicalResult?.criterion_results ?? []).filter((criterion) => {
    if (criterion.status === "failed") {
      return true;
    }
    if (criterion.passed === false) {
      return true;
    }
    return false;
  });

  return (
    <details className={styles.resultAccordion}>
      <summary className={styles.resultAccordionSummary}>
        <div className={styles.resultAccordionHeader}>
          <div>
            <div className={styles.resultAccordionTitle}>{scoreBreakdown.vendor_name}</div>
            <div className={styles.resultAccordionMeta}>
              {scoreBreakdown.vendor_id === winnerVendorId
                ? "Official winner"
                : scoreBreakdown.passed_technical_gate
                  ? "Passed the technical gate and entered ranking"
                  : "Stopped at the technical gate"}
            </div>
          </div>
          <div className={styles.resultAccordionSummaryMetrics}>
            <div className={styles.resultMetricPill}>
              <span className={styles.resultMetricLabel}>Final QCBS Score</span>
              <strong className={styles.resultMetricValue}>
                {formatOptionalNumber(scoreBreakdown.final_score)}
              </strong>
            </div>
            <div
              className={`${styles.statusBadge} ${
                scoreBreakdown.vendor_id === winnerVendorId
                  ? styles.statusBadgeSuccess
                  : scoreBreakdown.passed_technical_gate
                    ? styles.statusBadgeNeutral
                    : styles.statusBadgeDanger
              }`}
            >
              {scoreBreakdown.vendor_id === winnerVendorId
                ? "Winner"
                : scoreBreakdown.passed_technical_gate
                  ? "Ranked"
                  : "Disqualified"}
            </div>
          </div>
        </div>
      </summary>

      <div className={styles.resultAccordionBody}>
        <div className={styles.summaryGrid}>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Technical Score</span>
            <span className={styles.summaryValue}>{formatOptionalNumber(scoreBreakdown.technical_score)}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Commercial Score</span>
            <span className={styles.summaryValue}>{formatOptionalNumber(scoreBreakdown.commercial_score)}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Final QCBS Score</span>
            <span className={styles.summaryValue}>{formatOptionalNumber(scoreBreakdown.final_score)}</span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Technical Gate</span>
            <span className={styles.summaryValue}>
              {scoreBreakdown.passed_technical_gate ? "Passed" : "Failed"}
            </span>
          </div>
          <div className={styles.summaryItem}>
            <span className={styles.summaryLabel}>Commercial Status</span>
            <span className={styles.summaryValue}>
              {scoreBreakdown.commercially_comparable ? "Comparable" : "Blocked / not comparable"}
            </span>
          </div>
        </div>

        {technicalThreshold !== null ? (
          <div className={styles.frameworkNote}>
            Framework technical threshold: {formatOptionalNumber(technicalThreshold)} / 100.
          </div>
        ) : null}

        {technicalResult?.summary ? (
          <div className={styles.summaryNarrative}>
            <span className={styles.summaryLabel}>Technical Summary</span>
            <span className={styles.summaryValue}>{technicalResult.summary}</span>
          </div>
        ) : null}

        {failedTechnicalCriteria.length > 0 ? (
          <div className={styles.reviewInsightBox}>
            <span className={styles.summaryLabel}>Failed Technical Criteria / MAC</span>
            <div className={styles.previewList}>
              {failedTechnicalCriteria.map((criterion) => {
                const criterionDefinition = criteriaById.get(criterion.criterion_id) ?? null;
                return (
                  <div className={styles.previewItem} key={criterion.criterion_id}>
                    <div className={styles.previewItemHeader}>
                      <div className={styles.previewTitle}>
                        {criterionDefinition?.title ?? criterion.title}
                      </div>
                      <div className={styles.previewBadge}>
                        {formatCriterionOutcomeLabel(criterion, criterionDefinition)}
                      </div>
                    </div>
                    <div className={styles.previewItemMeta}>
                      {formatCriterionTypeForBuyer(criterionDefinition?.criterion_type ?? criterion.criterion_type)}
                    </div>
                    <div className={styles.previewItemBody}>{splitReasoningSummary(criterion.explanation).summaryText}</div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : null}

        <div className={styles.traceSection}>
          <div className={styles.traceSectionTitle}>Technical score trace</div>
          {technicalResult && (technicalResult.criterion_results ?? []).length > 0 ? (
            <div className={styles.tableWrap}>
              <table className={styles.scoreTable}>
                <thead>
                  <tr>
                    <th>Criterion</th>
                    <th>Criterion Type</th>
                    <th>Score / Outcome</th>
                    <th>Cutoff / Rule</th>
                    <th>Result</th>
                  </tr>
                </thead>
                <tbody>
                  {(technicalResult.criterion_results ?? []).map((criterion) => {
                    const criterionDefinition = criteriaById.get(criterion.criterion_id) ?? null;
                    return (
                      <tr key={`${scoreBreakdown.vendor_id}-${criterion.criterion_id}`}>
                        <td>{criterionDefinition?.title ?? criterion.title}</td>
                        <td>
                          {formatCriterionTypeForBuyer(
                            criterionDefinition?.criterion_type ?? criterion.criterion_type,
                          )}
                        </td>
                        <td>{formatCriterionScore(criterion, criterionDefinition)}</td>
                        <td>{formatCriterionCutoffForBuyer(criterionDefinition)}</td>
                        <td>{formatCriterionOutcomeLabel(criterion, criterionDefinition)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className={styles.previewEmpty}>No technical criterion trace is available.</div>
          )}
        </div>

        <div className={styles.traceSection}>
          <div className={styles.traceSectionTitle}>Commercial score trace</div>
          {commercialResult ? (
            <>
              <div className={styles.summaryNarrative}>
                <span className={styles.summaryLabel}>Commercial Summary</span>
                <span className={styles.summaryValue}>{commercialResult.explanation}</span>
              </div>

              {(commercialResult.line_items ?? []).length > 0 ? (
                <div className={styles.tableWrap}>
                  <table className={styles.scoreTable}>
                    <thead>
                      <tr>
                        <th>Line Item</th>
                        <th>Normalized Total</th>
                        <th>Comparison Status</th>
                        <th>Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(commercialResult.line_items ?? []).map((lineItem) => (
                        <tr key={`${scoreBreakdown.vendor_id}-${lineItem.line_item_id}`}>
                          <td>{lineItem.line_item_name}</td>
                          <td>
                            {formatOptionalNumber(lineItem.base_currency_total)} {commercialResult.base_currency}
                          </td>
                          <td>{formatComparabilityStatus(lineItem.comparability_status)}</td>
                          <td>{(lineItem.notes ?? []).join(" ") || "None"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className={styles.previewEmpty}>No normalized commercial line-item trace is available.</div>
              )}

              {(commercialResult.blockers ?? []).length > 0 ? (
                <div className={styles.reviewInsightBox}>
                  <span className={styles.summaryLabel}>Commercial Blockers</span>
                  <span className={styles.summaryValue}>{(commercialResult.blockers ?? []).join(" ")}</span>
                </div>
              ) : null}
            </>
          ) : (
            <div className={styles.previewEmpty}>No commercial trace is available for this vendor.</div>
          )}
        </div>
      </div>
    </details>
  );
}

function QuestionAnswerList({
  fields,
  questionLookup,
  criteriaByQuestionId,
  criterionResultsById,
}: {
  fields: ExtractedField[];
  questionLookup: Map<string, Question>;
  criteriaByQuestionId: Map<string, Criterion>;
  criterionResultsById: Map<string, TechnicalCriterionResult>;
}) {
  return (
    <div className={styles.previewSection} id="review-question-answers">
      <div className={styles.previewSectionTitle}>Question Answers</div>
      <div className={styles.previewItemMeta}>
        Collapsed view shows the vendor question, the criterion being judged, and the extracted answer. Expand a card
        to inspect evidence, confidence, risks, and internal traceability.
      </div>
      {fields.length === 0 ? (
        <div className={styles.previewEmpty}>No question answers were captured.</div>
      ) : (
        <div className={styles.previewList}>
          {fields.map((field) => {
            const question = field.question_id ? questionLookup.get(field.question_id) ?? null : null;
            const criterion = field.question_id ? criteriaByQuestionId.get(field.question_id) ?? null : null;
            const criterionResult = criterion ? criterionResultsById.get(criterion.id) ?? null : null;
            const { summaryText, reasoningText } = criterionResult
              ? splitReasoningSummary(criterionResult.explanation)
              : { summaryText: null, reasoningText: null };

            return (
              <details className={styles.reviewAnswerCard} key={field.id}>
                <summary className={styles.reviewAnswerSummary}>
                  <div className={styles.reviewAnswerSummaryHeader}>
                    <div className={styles.reviewAnswerSummaryBody}>
                      <div className={styles.reviewAnswerQuestion}>{question?.text ?? field.label}</div>
                      <div className={styles.reviewAnswerExcerpt}>
                        {field.raw_value ?? "No extracted answer was found."}
                      </div>
                    </div>
                  </div>
                </summary>

                <div className={styles.reviewAnswerDetail}>
                  <div className={styles.reviewDetailGrid}>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Criterion Being Judged</span>
                      <span className={styles.summaryValue}>
                        {criterion?.title ?? "No linked criterion found."}
                      </span>
                    </div>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Criterion Type</span>
                      <span className={styles.summaryValue}>
                        {criterion
                          ? formatCriterionTypeForBuyer(criterion.criterion_type)
                          : "Not available"}
                      </span>
                    </div>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Extracted Answer Status</span>
                      <span className={styles.summaryValue}>{field.state}</span>
                    </div>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Current Technical Outcome</span>
                      <span className={styles.summaryValue}>
                        {criterionResult
                          ? formatCriterionOutcomeLabel(criterionResult, criterion)
                          : "Available after technical evaluation is run."}
                      </span>
                    </div>
                  </div>
                  {criterion?.description ? (
                    <div className={styles.summaryNarrative}>
                      <span className={styles.summaryLabel}>What This Criterion Checks</span>
                      <span className={styles.summaryValue}>{criterion.description}</span>
                    </div>
                  ) : null}
                  {question?.purpose ? (
                    <div className={styles.summaryNarrative}>
                      <span className={styles.summaryLabel}>Why This Question Was Asked</span>
                      <span className={styles.summaryValue}>{question.purpose}</span>
                    </div>
                  ) : null}
                  <div className={styles.reviewInsightBox}>
                    <span className={styles.summaryLabel}>Supporting Evidence</span>
                    {(field.evidence ?? []).length > 0 ? (
                      <div className={styles.reviewEvidenceList}>
                        {(field.evidence ?? []).map((anchor) => (
                          <div className={styles.reviewEvidenceItem} key={anchor.id}>
                            <div className={styles.reviewEvidenceLocator}>{anchor.locator}</div>
                            <div className={styles.summaryValue}>{anchor.snippet}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <span className={styles.summaryValue}>No evidence snippet is available.</span>
                    )}
                  </div>
                  <div className={styles.reviewDetailGrid}>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Confidence</span>
                      <span className={styles.summaryValue}>
                        {criterionResult ? formatOptionalNumber(criterionResult.confidence) : "Available after evaluation"}
                      </span>
                    </div>
                    <div className={styles.summaryItem}>
                      <span className={styles.summaryLabel}>Minimum Qualifying Score</span>
                      <span className={styles.summaryValue}>{formatCriterionCutoffForBuyer(criterion)}</span>
                    </div>
                  </div>
                  <div className={styles.reviewInsightBox}>
                    <span className={styles.summaryLabel}>Evaluation Risk</span>
                    <span className={styles.summaryValue}>
                      {criterionResult
                        ? (criterionResult.risks ?? []).join(" ") || "No explicit risk was flagged for this criterion."
                        : "Available after technical evaluation is run."}
                    </span>
                  </div>
                  {criterionResult ? (
                    <div className={styles.reviewInsightBox}>
                      <span className={styles.summaryLabel}>Evaluation Summary</span>
                      <span className={styles.summaryValue}>{summaryText || "No evaluation summary available."}</span>
                    </div>
                  ) : null}
                  {reasoningText ? (
                    <div className={styles.summaryNarrative}>
                      <span className={styles.summaryLabel}>AI Reasoning Note</span>
                      <span className={styles.summaryValue}>{reasoningText}</span>
                    </div>
                  ) : null}
                  <details className={styles.advancedPanel}>
                    <summary className={styles.advancedSummary}>
                      <span>View Traceability Detail</span>
                      <span className={styles.advancedMeta}>{field.id}</span>
                    </summary>
                    <div className={styles.advancedBody}>
                      <div className={styles.summaryNarrative}>
                        <span className={styles.summaryLabel}>Question ID</span>
                        <span className={styles.summaryValue}>{field.question_id ?? "None"}</span>
                      </div>
                      <div className={styles.summaryNarrative}>
                        <span className={styles.summaryLabel}>Criterion ID</span>
                        <span className={styles.summaryValue}>{criterion?.id ?? "None"}</span>
                      </div>
                      <div className={styles.summaryNarrative}>
                        <span className={styles.summaryLabel}>Extracted Field ID</span>
                        <span className={styles.summaryValue}>{field.id}</span>
                      </div>
                      {(criterionResult?.evidence_refs ?? []).length > 0 ? (
                        <div className={styles.summaryNarrative}>
                          <span className={styles.summaryLabel}>Evaluation Evidence IDs</span>
                          <span className={styles.summaryValue}>
                            {(criterionResult?.evidence_refs ?? []).join(", ")}
                          </span>
                        </div>
                      ) : null}
                    </div>
                  </details>
                </div>
              </details>
            );
          })}
        </div>
      )}
    </div>
  );
}

function FieldGroupList({
  title,
  fields,
  sectionId,
}: {
  title: string;
  fields: ExtractedField[];
  sectionId?: string;
}) {
  return (
    <div className={styles.previewSection} id={sectionId}>
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

function TechnicalCriterionCard({
  criterionDefinition,
  evidenceLookup,
  questionLookup,
  result,
}: {
  criterionDefinition: Criterion | null;
  evidenceLookup: Map<string, string>;
  questionLookup: Map<string, Question>;
  result: TechnicalCriterionResult;
}) {
  const { summaryText, reasoningText } = splitReasoningSummary(result.explanation);
  const evidenceSnippets = (result.evidence_refs ?? [])
    .map((evidenceId) => evidenceLookup.get(evidenceId))
    .filter((snippet): snippet is string => Boolean(snippet));
  const vendorQuestion = getCriterionQuestionText(criterionDefinition, questionLookup);

  return (
    <div className={styles.previewItem}>
      <div className={styles.previewItemHeader}>
        <div className={styles.previewTitle}>{criterionDefinition?.title ?? result.title}</div>
        <div className={styles.previewBadge}>{formatCriterionOutcomeLabel(result, criterionDefinition)}</div>
      </div>
      <div className={styles.summaryGrid}>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Criterion Type</span>
          <span className={styles.summaryValue}>
            {formatCriterionTypeForBuyer(criterionDefinition?.criterion_type ?? result.criterion_type)}
          </span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Score</span>
          <span className={styles.summaryValue}>{formatCriterionScore(result, criterionDefinition)}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Minimum Qualifying Score</span>
          <span className={styles.summaryValue}>{formatCriterionCutoffForBuyer(criterionDefinition)}</span>
        </div>
        <div className={styles.summaryItem}>
          <span className={styles.summaryLabel}>Confidence</span>
          <span className={styles.summaryValue}>{formatOptionalNumber(result.confidence)}</span>
        </div>
      </div>
      {criterionDefinition?.description ? (
        <div className={styles.summaryNarrative} style={{ marginTop: 10 }}>
          <span className={styles.summaryLabel}>What This Criterion Checks</span>
          <span className={styles.summaryValue}>{criterionDefinition.description}</span>
        </div>
      ) : null}
      {vendorQuestion ? (
        <div className={styles.summaryNarrative} style={{ marginTop: 10 }}>
          <span className={styles.summaryLabel}>Vendor Question</span>
          <span className={styles.summaryValue}>{vendorQuestion}</span>
        </div>
      ) : null}
      <div className={styles.summaryNarrative} style={{ marginTop: 10 }}>
        <span className={styles.summaryLabel}>Evaluation Summary</span>
        <span className={styles.summaryValue}>{summaryText}</span>
      </div>
      <div className={styles.summaryNarrative} style={{ marginTop: 10 }}>
        <span className={styles.summaryLabel}>Supporting Evidence</span>
        <span className={styles.summaryValue}>
          {evidenceSnippets.length > 0
            ? evidenceSnippets.join(" | ")
            : "No buyer-readable evidence snippet is available for this criterion."}
        </span>
      </div>
      {(result.risks ?? []).length > 0 ? (
        <div className={styles.summaryNarrative} style={{ marginTop: 10 }}>
          <span className={styles.summaryLabel}>Risks</span>
          <span className={styles.summaryValue}>{(result.risks ?? []).join(" ")}</span>
        </div>
      ) : null}
      <details className={styles.advancedPanel} style={{ marginTop: 10 }}>
        <summary className={styles.advancedSummary}>
          <span>View Scoring Detail</span>
          <span className={styles.advancedMeta}>{result.criterion_id}</span>
        </summary>
        <div className={styles.advancedBody}>
          {reasoningText ? (
            <div className={styles.summaryNarrative}>
              <span className={styles.summaryLabel}>AI Reasoning Note</span>
              <span className={styles.summaryValue}>{reasoningText}</span>
            </div>
          ) : null}
          {(result.math_trace ?? []).length > 0 ? (
            <div className={styles.summaryNarrative}>
              <span className={styles.summaryLabel}>Scoring Trace</span>
              <span className={styles.summaryValue}>{(result.math_trace ?? []).join(" ")}</span>
            </div>
          ) : null}
          <div className={styles.summaryNarrative}>
            <span className={styles.summaryLabel}>Evidence Reference IDs</span>
            <span className={styles.summaryValue}>{(result.evidence_refs ?? []).join(", ") || "None"}</span>
          </div>
        </div>
      </details>
    </div>
  );
}

function NormalizedFieldList({
  fields,
  rfqCurrency,
  sectionId,
}: {
  fields: NormalizedField[];
  rfqCurrency: string | null;
  sectionId?: string;
}) {
  return (
    <div className={styles.previewSection} id={sectionId}>
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
                Converted value in RFQ currency: {formatOptionalNumber(field.base_currency_value)} {rfqCurrency ?? ""}
                {" | "}
                RFQ UOM: {field.target_uom ?? "N/A"}
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

function NormalizedPricingTable({
  pricingLines,
  rfqCurrency,
  sectionId,
}: {
  pricingLines: NormalizedPricingLine[];
  rfqCurrency: string | null;
  sectionId?: string;
}) {
  return (
    <div className={styles.previewSection} id={sectionId}>
      <div className={styles.previewSectionTitle}>Normalized Pricing</div>
      <div className={styles.tableWrap}>
        <table className={styles.scoreTable}>
          <thead>
            <tr>
              <th>Line Item</th>
              <th>Vendor Quoted Price</th>
              <th>Vendor Currency</th>
              <th>Vendor UOM</th>
              <th>RFQ Currency</th>
              <th>RFQ UOM</th>
              <th>Converted Price In RFQ Currency</th>
              <th>Comparison Status</th>
              <th>Conversion Applied</th>
              <th>Buyer Notes / Blockers</th>
            </tr>
          </thead>
          <tbody>
            {pricingLines.map((line) => (
              <tr key={line.line_item_id}>
                <td>{line.line_item_name}</td>
                <td>{formatOptionalNumber(line.total_price)}</td>
                <td>{line.currency ?? "N/A"}</td>
                <td>{line.uom ?? "N/A"}</td>
                <td>{rfqCurrency ?? "N/A"}</td>
                <td>{line.target_uom ?? "N/A"}</td>
                <td>{formatOptionalNumber(line.base_currency_total)}</td>
                <td>{line.comparability_status}</td>
                <td>{(line.conversion_notes ?? []).join(" ") || "No currency or UOM conversion was applied."}</td>
                <td>{[...(line.exclusions ?? []), ...(line.blockers ?? [])].join(" ") || "None"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function buildEvidenceLookup(review: VendorReview): Map<string, string> {
  const lookup = new Map<string, string>();
  for (const field of [
    ...(review.raw_extraction.question_answers ?? []),
    ...(review.raw_extraction.schedule_answers ?? []),
    ...(review.raw_extraction.technical_claims ?? []),
    ...(review.raw_extraction.commercial_claims ?? []),
  ]) {
    for (const anchor of field.evidence ?? []) {
      if (!lookup.has(anchor.id)) {
        lookup.set(anchor.id, `${anchor.locator}: ${anchor.snippet}`);
      }
    }
  }
  return lookup;
}

function rankVendorBreakdowns(
  scoreBreakdown: VendorScoreBreakdownItem[],
  winnerVendorId: string | null,
): VendorScoreBreakdownItem[] {
  return [...scoreBreakdown].sort((left, right) => {
    if (winnerVendorId) {
      if (left.vendor_id === winnerVendorId && right.vendor_id !== winnerVendorId) {
        return -1;
      }
      if (right.vendor_id === winnerVendorId && left.vendor_id !== winnerVendorId) {
        return 1;
      }
    }

    const finalDelta = safeSortableNumber(right.final_score) - safeSortableNumber(left.final_score);
    if (finalDelta !== 0) {
      return finalDelta;
    }

    const technicalDelta =
      safeSortableNumber(right.technical_score) - safeSortableNumber(left.technical_score);
    if (technicalDelta !== 0) {
      return technicalDelta;
    }

    return left.vendor_name.localeCompare(right.vendor_name);
  });
}

function buildPodiumEntries(
  scoreBreakdown: VendorScoreBreakdownItem[],
  winnerVendorId: string | null,
): VendorScoreBreakdownItem[] {
  const ranked = rankVendorBreakdowns(scoreBreakdown, winnerVendorId);
  return ranked.slice(0, 3);
}

function safeSortableNumber(value: number | null | undefined): number {
  if (typeof value !== "number" || Number.isNaN(value)) {
    return Number.NEGATIVE_INFINITY;
  }
  return value;
}

function splitReasoningSummary(text: string): { summaryText: string; reasoningText: string | null } {
  const marker = "Reasoning summary:";
  const index = text.indexOf(marker);
  if (index === -1) {
    return { summaryText: text, reasoningText: null };
  }

  return {
    summaryText: text.slice(0, index).trim(),
    reasoningText: text.slice(index + marker.length).trim(),
  };
}

function getCriterionQuestionText(
  criterionDefinition: Criterion | null,
  questionLookup: Map<string, Question>,
): string | null {
  if (criterionDefinition?.vendor_question?.text) {
    return criterionDefinition.vendor_question.text;
  }
  const questionId = criterionDefinition?.linked_question_ids?.[0];
  if (!questionId) {
    return null;
  }
  return questionLookup.get(questionId)?.text ?? null;
}

function formatCriterionTypeForBuyer(criterionType: string): string {
  switch (criterionType) {
    case "mac":
      return "Mandatory requirement (pass/fail)";
    case "technical_cutoff_backed":
      return "Scored technical criterion with a minimum qualifying score";
    case "technical_scored_only":
      return "Scored technical criterion without an individual cutoff";
    case "commercial":
      return "Commercial criterion";
    default:
      return criterionType;
  }
}

function formatCriterionScore(result: TechnicalCriterionResult, criterionDefinition: Criterion | null): string {
  const maxScore = criterionDefinition?.max_score ?? result.max_score;
  if (criterionDefinition?.criterion_type === "mac" || result.criterion_type === "mac") {
    return result.passed ? "Pass" : "Fail";
  }
  if (typeof result.score !== "number") {
    return maxScore !== null && maxScore !== undefined ? `N/A / ${formatOptionalNumber(maxScore)}` : "N/A";
  }
  return maxScore !== null && maxScore !== undefined
    ? `${formatOptionalNumber(result.score)} / ${formatOptionalNumber(maxScore)}`
    : formatOptionalNumber(result.score);
}

function formatCriterionCutoffForBuyer(criterionDefinition: Criterion | null): string {
  if (!criterionDefinition) {
    return "Not available";
  }
  if (criterionDefinition.criterion_type === "mac") {
    return "Pass / Fail";
  }
  if (criterionDefinition.criterion_type === "technical_scored_only") {
    return "None";
  }
  if (criterionDefinition.criterion_type === "commercial") {
    return "Not applicable";
  }
  if (typeof criterionDefinition.min_cutoff === "number" && typeof criterionDefinition.max_score === "number") {
    return `${formatOptionalNumber(criterionDefinition.min_cutoff)} / ${formatOptionalNumber(criterionDefinition.max_score)}`;
  }
  if (typeof criterionDefinition.min_cutoff === "number") {
    return formatOptionalNumber(criterionDefinition.min_cutoff);
  }
  return "Not set";
}

function formatComparabilityStatus(status: string): string {
  switch (status) {
    case "comparable":
      return "Comparable";
    case "needs_buyer_input":
      return "Needs buyer input";
    case "non_comparable":
      return "Not comparable";
    case "informational":
      return "Informational only";
    default:
      return status;
  }
}

function formatCriterionOutcomeLabel(result: TechnicalCriterionResult, criterionDefinition: Criterion | null): string {
  const criterionType = criterionDefinition?.criterion_type ?? result.criterion_type;
  if (criterionType === "mac") {
    return result.passed ? "Mandatory gate passed" : "Mandatory gate failed";
  }
  if (criterionType === "technical_cutoff_backed") {
    const cutoff = criterionDefinition?.min_cutoff;
    if (typeof result.score === "number" && typeof cutoff === "number") {
      return result.score >= cutoff
        ? `Cutoff met · ${formatOptionalNumber(result.score)}`
        : `Cutoff not met · ${formatOptionalNumber(result.score)}`;
    }
  }
  if (typeof result.score === "number") {
    return `Scored · ${formatOptionalNumber(result.score)}`;
  }
  return result.status;
}

function scrollToReviewSection(sectionId: string) {
  const element = document.getElementById(sectionId);
  if (!element) {
    return;
  }
  element.scrollIntoView({ behavior: "smooth", block: "start" });
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
