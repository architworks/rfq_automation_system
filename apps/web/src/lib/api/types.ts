import type { components } from "./generated";

export type BuyerPriority = components["schemas"]["BuyerPriority"];
export type Criterion = components["schemas"]["Criterion"];
export type CriterionType = components["schemas"]["CriterionType"];
export type DownloadMetadata = components["schemas"]["DownloadMetadata"];
export type EvidenceCheck = components["schemas"]["EvidenceCheck"];
export type GeneralInfo = components["schemas"]["GeneralInfo"];
export type GovernanceInfo = components["schemas"]["GovernanceInfo"];
export type LineItem = components["schemas"]["LineItem"];
export type LockedFrameworkArtifact = components["schemas"]["LockedFrameworkArtifact"];
export type Question = components["schemas"]["Question"];
export type ResponseSchedule = components["schemas"]["ResponseSchedule"];
export type RFQDraft = components["schemas"]["RFQDraft"];
export type RubricProposal = components["schemas"]["RubricProposal-Output"];
export type RubricProposalInput = components["schemas"]["RubricProposal-Input"];
export type RubricSection = components["schemas"]["RubricSection"];
export type ScheduleColumn = components["schemas"]["ScheduleColumn"];
export type SessionSnapshot = components["schemas"]["SessionSnapshot"];
export type SessionStatus = components["schemas"]["SessionStatus"];
export type TimelineItem = components["schemas"]["TimelineItem"];
export interface ValidationIssue {
  field: string;
  message: string;
}

export const OFFICIAL_AWARD_BASIS = "QCBS 70/30";
