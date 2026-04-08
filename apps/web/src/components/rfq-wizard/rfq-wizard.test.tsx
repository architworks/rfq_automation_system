import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ApiError, OFFICIAL_AWARD_BASIS, type LockedFrameworkArtifact, type RFQDraft, type RfqApiClient, type RubricProposal, type SessionSnapshot } from "@/lib/api";

import { RfqWizard } from "./rfq-wizard";

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function createSeededDraft(overrides?: Partial<RFQDraft>): RFQDraft {
  const draft: RFQDraft = {
    general_info: {
      title: "Global Kids Health Drink Launch Partner RFQ",
      rfq_code: "RFQ-KHD-2026-001",
      owner: "Growth Procurement",
      region: "India",
    },
    scope_overview:
      "Appoint an integrated agency partner to launch a kids health drink across creative, production, social, and governance workstreams.",
    timelines: [
      {
        id: "timeline_1",
        label: "RFQ Release",
        target_date: "2026-04-15",
        description: "Buyer releases the RFQ pack.",
      },
      {
        id: "timeline_2",
        label: "Agency Onboarding",
        target_date: "2026-06-01",
        description: "Selected partner starts the launch workstream.",
      },
    ],
    buyer_priorities: [
      {
        id: "priority_1",
        title: "Launch readiness",
        description: "Need a partner who can mobilize quickly and handle cross-functional orchestration.",
      },
      {
        id: "priority_2",
        title: "Compliance discipline",
        description: "Claims and kids advertising compliance are critical decision factors.",
      },
    ],
    mandatory_conditions: [
      "Agency must disclose all subcontractors and production partners.",
      "All claims and kids advertising work must follow applicable compliance norms.",
    ],
    line_items: [
      {
        id: "line_item_1",
        product_name: "Strategy & Creative Development",
        category: "Services",
        description: "Brand launch strategy, message architecture, and creative platform.",
        hsn_sac: "998361",
        uom: "Lot",
      },
      {
        id: "line_item_2",
        product_name: "TVC Development",
        category: "Services",
        description: "Storyboard, scripting, and production planning for launch film.",
        hsn_sac: "998362",
        uom: "Lot",
      },
      {
        id: "line_item_3",
        product_name: "TVC Production",
        category: "Services",
        description: "End-to-end film production for launch campaign.",
        hsn_sac: "998363",
        uom: "Lot",
      },
      {
        id: "line_item_4",
        product_name: "Social Organic Content",
        category: "Services",
        description: "Organic social content planning and production.",
        hsn_sac: "998364",
        uom: "Lot",
      },
      {
        id: "line_item_5",
        product_name: "Social Paid Media Planning",
        category: "Services",
        description: "Paid media channel and investment planning.",
        hsn_sac: "998365",
        uom: "Lot",
      },
      {
        id: "line_item_6",
        product_name: "Social Paid Media Buying & Optimization",
        category: "Services",
        description: "Execution, monitoring, and optimization of paid campaigns.",
        hsn_sac: "998366",
        uom: "Lot",
      },
      {
        id: "line_item_7",
        product_name: "Kids Advertising & Claims Compliance Review",
        category: "Services",
        description: "Independent compliance review for kids and claims-heavy materials.",
        hsn_sac: "998367",
        uom: "Lot",
      },
      {
        id: "line_item_8",
        product_name: "Launch Program Management",
        category: "Services",
        description: "Program tracking, milestone governance, and stakeholder coordination.",
        hsn_sac: "998368",
        uom: "Lot",
      },
    ],
  };

  return {
    ...draft,
    ...overrides,
  };
}

function createRubricProposal(): RubricProposal {
  return {
    sections: [
      {
        id: "section_technical",
        title: "Technical Evaluation",
        description: "Criteria used to assess technical merit and readiness.",
      },
      {
        id: "section_commercial",
        title: "Commercial Evaluation",
        description: "Commercial disclosures for later QCBS analysis.",
      },
    ],
    criteria: [
      {
        id: "criterion_experience",
        section_id: "section_technical",
        title: "Relevant launch experience",
        description: "Experience launching nutrition or kids-focused brands at national scale.",
        criterion_type: "technical_cutoff_backed",
        weight: 60,
        min_cutoff: 6,
        max_score: 10,
        evidence_checks: [
          {
            id: "evidence_case_studies",
            label: "Comparable case studies",
            description: "At least two relevant launches in the last three years.",
          },
        ],
        linked_question_ids: ["question_experience"],
        linked_schedule_fields: ["schedule_team.lead_experience"],
      },
      {
        id: "criterion_governance",
        section_id: "section_technical",
        title: "Program governance",
        description: "Ability to manage the launch program with clear accountability and cadence.",
        criterion_type: "technical_scored_only",
        weight: 40,
        min_cutoff: null,
        max_score: 10,
        evidence_checks: [
          {
            id: "evidence_governance",
            label: "Governance model",
            description: "Describe operating model and reporting rhythm.",
          },
        ],
        linked_question_ids: ["question_governance"],
        linked_schedule_fields: ["schedule_team.program_lead"],
      },
      {
        id: "criterion_pricing",
        section_id: "section_commercial",
        title: "Commercial submission",
        description: "Commercial schedules will feed the downstream QCBS step.",
        criterion_type: "commercial",
        weight: null,
        min_cutoff: null,
        max_score: 10,
        evidence_checks: [
          {
            id: "evidence_commercial",
            label: "Commercial schedule completeness",
            description: "All commercial fields populated.",
          },
        ],
        linked_question_ids: [],
        linked_schedule_fields: ["schedule_commercial.total_fee"],
      },
    ],
    aggregate_technical_threshold: 70,
    questions: [
      {
        id: "question_experience",
        text: "Describe two comparable launch engagements and their outcomes.",
        purpose: "Validate relevant launch experience.",
        linked_criteria: ["criterion_experience"],
      },
      {
        id: "question_governance",
        text: "Describe the team structure, reporting cadence, and decision governance.",
        purpose: "Validate execution governance.",
        linked_criteria: ["criterion_governance"],
      },
    ],
    response_schedules: [
      {
        id: "schedule_team",
        name: "Team Schedule",
        purpose: "Capture proposed team structure and experience.",
        linked_criteria: ["criterion_experience", "criterion_governance"],
        columns: [
          {
            id: "lead_experience",
            label: "Lead Experience",
            description: "Years and relevant category exposure for the account lead.",
            required: true,
          },
          {
            id: "program_lead",
            label: "Program Lead",
            description: "Named program lead and governance owner.",
            required: true,
          },
        ],
      },
      {
        id: "schedule_commercial",
        name: "Commercial Schedule",
        purpose: "Capture fee and commercial structure for later QCBS analysis.",
        linked_criteria: ["criterion_pricing"],
        columns: [
          {
            id: "total_fee",
            label: "Total Fee",
            description: "Overall quoted commercial value.",
            required: true,
          },
        ],
      },
    ],
    official_award_basis: OFFICIAL_AWARD_BASIS,
    generation_rationale: [
      "Prioritize launch experience and governance because the RFQ demands fast mobilization.",
      "Keep commercial capture structured for downstream QCBS without altering the fixed award basis.",
    ],
  };
}

function createLockedArtifact(
  rfqDraft: RFQDraft,
  rubricProposal: RubricProposal,
  sessionId: string,
): LockedFrameworkArtifact {
  return {
    version: "1.0",
    locked_at: "2026-04-08T18:00:00Z",
    rfq_snapshot: cloneValue(rfqDraft),
    rubric_snapshot: cloneValue(rubricProposal),
    governance: {
      official_award_basis: OFFICIAL_AWARD_BASIS,
      technical_threshold_strategy:
        "RFQ-specific threshold proposed by AI and approved by buyer before lock.",
      advisory_outputs: ["LCS", "QBS", "RFQ-specific AI scenarios"],
      persistence_scope: "Browser session plus in-memory backend session state with TTL.",
    },
    download_metadata: {
      file_name: `locked-framework-${sessionId}.json`,
      content_type: "application/json",
    },
  };
}

function createSessionSnapshot(options?: {
  sessionId?: string;
  title?: string;
  withRubric?: boolean;
  withArtifact?: boolean;
}): SessionSnapshot {
  const sessionId = options?.sessionId ?? "session_123";
  const rfqDraft = createSeededDraft({
    general_info: {
      title: options?.title ?? "Global Kids Health Drink Launch Partner RFQ",
      rfq_code: "RFQ-KHD-2026-001",
      owner: "Growth Procurement",
      region: "India",
    },
  });
  const rubricProposal = options?.withRubric === false ? null : createRubricProposal();
  const lockedArtifact =
    options?.withArtifact && rubricProposal
      ? createLockedArtifact(rfqDraft, rubricProposal, sessionId)
      : null;

  return {
    session_id: sessionId,
    status: lockedArtifact ? "locked" : rubricProposal ? "proposal_ready" : "draft",
    rfq_draft: rfqDraft,
    rubric_proposal: rubricProposal,
    locked_artifact: lockedArtifact,
    updated_at: "2026-04-08T17:00:00Z",
  };
}

function createStatefulApi(
  initialSnapshot: SessionSnapshot,
  options?: {
    generateError?: Error;
    lockError?: Error;
  },
): { api: RfqApiClient; readSnapshot: () => SessionSnapshot } {
  let snapshot = cloneValue(initialSnapshot);

  const api: RfqApiClient = {
    createOrHydrateSession: vi.fn(async () => cloneValue(snapshot)),
    getSession: vi.fn(async () => cloneValue(snapshot)),
    saveRfq: vi.fn(async (_sessionId, draft) => {
      snapshot = {
        ...snapshot,
        rfq_draft: cloneValue(draft),
        updated_at: "2026-04-08T17:05:00Z",
      };
      return cloneValue(snapshot);
    }),
    generateRubric: vi.fn(async () => {
      if (options?.generateError) {
        throw options.generateError;
      }

      snapshot = {
        ...snapshot,
        status: "proposal_ready",
        rubric_proposal: snapshot.rubric_proposal ?? createRubricProposal(),
        updated_at: "2026-04-08T17:10:00Z",
      };
      return cloneValue(snapshot);
    }),
    saveRubric: vi.fn(async (_sessionId, proposal) => {
      snapshot = {
        ...snapshot,
        rubric_proposal: cloneValue(proposal),
        updated_at: "2026-04-08T17:15:00Z",
      };
      return cloneValue(snapshot);
    }),
    lockRubric: vi.fn(async (sessionId) => {
      if (options?.lockError) {
        throw options.lockError;
      }

      const rubricProposal = snapshot.rubric_proposal ?? createRubricProposal();
      const artifact = createLockedArtifact(snapshot.rfq_draft, rubricProposal, sessionId);
      snapshot = {
        ...snapshot,
        status: "locked",
        rubric_proposal: rubricProposal,
        locked_artifact: artifact,
        updated_at: "2026-04-08T17:20:00Z",
      };
      return cloneValue(artifact);
    }),
    downloadArtifact: vi.fn(async () => ({
      blob: new Blob([JSON.stringify(snapshot.locked_artifact ?? null)], {
        type: "application/json",
      }),
      fileName: snapshot.locked_artifact?.download_metadata.file_name ?? "locked-framework.json",
    })),
  };

  return {
    api,
    readSnapshot: () => cloneValue(snapshot),
  };
}

describe("RfqWizard", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("loads the seeded RFQ on first session render", async () => {
    const { api } = createStatefulApi(createSessionSnapshot({ withRubric: false }));

    render(
      <RfqWizard
        api={api}
        autosaveMs={5}
        onStepChange={vi.fn()}
        sessionId="session_123"
        step="input"
      />,
    );

    expect(await screen.findByDisplayValue("Global Kids Health Drink Launch Partner RFQ")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Strategy & Creative Development")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Launch Program Management")).toBeInTheDocument();
  });

  it("keeps buyer RFQ edits across step changes and refresh within the same session", async () => {
    const { api, readSnapshot } = createStatefulApi(createSessionSnapshot());
    const onStepChange = vi.fn();

    const firstRender = render(
      <RfqWizard api={api} autosaveMs={25} onStepChange={onStepChange} sessionId="session_123" step="input" />,
    );

    const titleInput = await screen.findByLabelText("RFQ Title");
    fireEvent.change(titleInput, { target: { value: "Edited RFQ Title" } });

    await waitFor(() => {
      expect(api.saveRfq).toHaveBeenCalledTimes(1);
    });

    firstRender.rerender(
      <RfqWizard api={api} autosaveMs={25} onStepChange={onStepChange} sessionId="session_123" step="proposal" />,
    );

    expect(screen.getByText("Rubric Governance")).toBeInTheDocument();

    firstRender.unmount();

    render(
      <RfqWizard api={api} autosaveMs={25} onStepChange={onStepChange} sessionId="session_123" step="input" />,
    );

    expect(await screen.findByDisplayValue("Edited RFQ Title")).toBeInTheDocument();
    expect(readSnapshot().rfq_draft.general_info.title).toBe("Edited RFQ Title");
  });

  it("shows generation errors without losing RFQ input", async () => {
    const { api, readSnapshot } = createStatefulApi(createSessionSnapshot({ withRubric: false }), {
      generateError: new Error("Azure rubric generation failed."),
    });

    render(
      <RfqWizard
        api={api}
        autosaveMs={5}
        onStepChange={vi.fn()}
        sessionId="session_123"
        step="input"
      />,
    );

    const titleInput = await screen.findByLabelText("RFQ Title");
    fireEvent.change(titleInput, { target: { value: "Retry-safe RFQ Title" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate AI rubric" }));

    expect(await screen.findByText(/Request failed\./)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Retry-safe RFQ Title")).toBeInTheDocument();
    expect(readSnapshot().rfq_draft.general_info.title).toBe("Retry-safe RFQ Title");
    expect(api.generateRubric).toHaveBeenCalledTimes(1);
  });

  it("surfaces field-level validation errors on the lock screen", async () => {
    const { api } = createStatefulApi(createSessionSnapshot(), {
      lockError: new ApiError("Validation failed", 422, [
        {
          field: "criteria[0].min_cutoff",
          message: "Cutoff must fall within the score range.",
        },
        {
          field: "aggregate_technical_threshold",
          message: "Technical threshold must be between 0 and 100.",
        },
      ]),
    });

    render(
      <RfqWizard api={api} autosaveMs={5} onStepChange={vi.fn()} sessionId="session_123" step="lock" />,
    );

    expect(await screen.findByText("Lock Review")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Lock framework" }));

    expect(await screen.findByText("Lock validation failed.")).toBeInTheDocument();
    expect(screen.getByText(/criteria\[0\]\.min_cutoff/)).toBeInTheDocument();
    expect(screen.getByText(/aggregate_technical_threshold/)).toBeInTheDocument();
    expect(screen.getByText(/Technical threshold must be between 0 and 100\./)).toBeInTheDocument();
  });
});
