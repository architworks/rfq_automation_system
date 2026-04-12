import type {
  BuyerPriority,
  Criterion,
  CriterionType,
  DeterministicScoringGuide,
  DeterministicScoringRule,
  EvidenceCheck,
  LineItem,
  Question,
  RFQTimelineSet,
  ResponseSchedule,
  RubricSection,
  ScheduleColumn,
} from "@/lib/api/types";

function createId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

export function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export function createTimelineSet(): RFQTimelineSet {
  return {
    clarifications_deadline: "",
    technical_bid_deadline: "",
    commercial_bid_deadline: "",
    evaluation_start_date: "",
    negotiation_start_date: "",
    final_award_date: "",
  };
}

export function createBuyerPriority(): BuyerPriority {
  return {
    id: createId("priority"),
    title: "",
    description: "",
  };
}

export function createLineItem(): LineItem {
  return {
    id: createId("line_item"),
    product_name: "",
    category: "",
    description: "",
    hsn_sac: "",
    uom: "",
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

export function createDeterministicScoringRule(): DeterministicScoringRule {
  return {
    id: createId("score_rule"),
    condition: "New scoring condition",
    score: 0,
    outcome: null,
  };
}

export function createDeterministicScoringGuide(): DeterministicScoringGuide {
  return {
    guide_type: "pass_fail",
    answer_format: "Yes/No confirmation",
    summary: "Explain how this objective answer will be graded.",
    rules: [
      {
        id: createId("score_rule"),
        condition: "Condition satisfied",
        score: null,
        outcome: "pass",
      },
      {
        id: createId("score_rule"),
        condition: "Condition not satisfied",
        score: null,
        outcome: "fail",
      },
    ],
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
    deterministic_scoring: null,
    qualitative_scoring_guidance: null,
  };
}

export const CRITERION_TYPE_OPTIONS: Array<{ value: CriterionType; label: string }> = [
  { value: "mac", label: "Mandatory Gate (Pass/Fail)" },
  {
    value: "technical_cutoff_backed",
    label: "Scored Criterion with Minimum Qualifying Score",
  },
  {
    value: "technical_scored_only",
    label: "Scored Criterion without Individual Cutoff",
  },
  { value: "commercial", label: "Commercial Capture Only" },
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
