import type {
  BuyerPriority,
  Criterion,
  CriterionType,
  EvidenceCheck,
  LineItem,
  Question,
  ResponseSchedule,
  RubricSection,
  ScheduleColumn,
  TimelineItem,
} from "@/lib/api/types";

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function createTimelineItem(): TimelineItem {
  return {
    id: createId("timeline"),
    label: "New milestone",
    target_date: "2026-06-01",
    description: "",
  };
}

export function createBuyerPriority(): BuyerPriority {
  return {
    id: createId("priority"),
    title: "New buyer priority",
    description: "",
  };
}

export function createLineItem(): LineItem {
  return {
    id: createId("line_item"),
    product_name: "New line item",
    category: "Services",
    description: "",
    hsn_sac: "8471XX",
    uom: "Lot",
  };
}

export function createSection(): RubricSection {
  return {
    id: createId("section"),
    title: "New section",
    description: "",
  };
}

export function createEvidenceCheck(): EvidenceCheck {
  return {
    id: createId("evidence"),
    label: "New evidence check",
    description: "",
  };
}

export function createQuestion(): Question {
  return {
    id: createId("question"),
    text: "New question",
    purpose: "",
    linked_criteria: [],
  };
}

export function createScheduleColumn(): ScheduleColumn {
  return {
    id: createId("column"),
    label: "New column",
    description: "",
    required: true,
  };
}

export function createResponseSchedule(): ResponseSchedule {
  return {
    id: createId("schedule"),
    name: "New schedule",
    purpose: "",
    linked_criteria: [],
    columns: [createScheduleColumn()],
  };
}

export function createCriterion(
  sectionId: string,
  criterionType: CriterionType = "technical_scored_only",
): Criterion {
  return {
    id: createId("criterion"),
    section_id: sectionId,
    title: "New criterion",
    description: "",
    criterion_type: criterionType,
    weight: criterionType === "mac" || criterionType === "commercial" ? null : 0,
    min_cutoff: criterionType === "technical_cutoff_backed" ? 0 : null,
    max_score: criterionType === "mac" ? null : 10,
    evidence_checks: [createEvidenceCheck()],
    linked_question_ids: [],
    linked_schedule_fields: [],
  };
}

export const CRITERION_TYPE_OPTIONS: Array<{ value: CriterionType; label: string }> = [
  { value: "mac", label: "MAC" },
  { value: "technical_cutoff_backed", label: "Technical Cutoff-Backed" },
  { value: "technical_scored_only", label: "Technical Scored-Only" },
  { value: "commercial", label: "Commercial" },
];

export function parseCsv(value: string): string[] {
  return value
    .split(",")
    .map((entry) => entry.trim())
    .filter(Boolean);
}

export function toCsv(values: string[] | undefined): string {
  return (values ?? []).join(", ");
}
