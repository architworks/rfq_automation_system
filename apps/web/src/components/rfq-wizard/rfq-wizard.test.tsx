import { fireEvent, render, screen, waitFor } from "@testing-library/react";

import { ApiError, OFFICIAL_AWARD_BASIS, type LockedFrameworkArtifact, type RFQDraft, type RfqApiClient, type RubricProposal, type SessionSnapshot } from "@/lib/api";

import { RfqWizard } from "./rfq-wizard";

function cloneValue<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function createBlankDraft(overrides?: Partial<RFQDraft>): RFQDraft {
  const draft: RFQDraft = {
    general_info: {
      subject: "",
      rfq_code: "",
      sourcing_type: "",
      round: "",
      status: "",
      owner: "",
      currency: "",
      requestor: "",
      department: "",
      category: "",
    },
    scope_overview: "",
    timelines: {
      clarifications_deadline: "",
      technical_bid_deadline: "",
      commercial_bid_deadline: "",
      evaluation_start_date: "",
      negotiation_start_date: "",
      final_award_date: "",
    },
    buyer_priorities: [],
    mandatory_conditions: [],
    line_items: [],
  };

  return {
    ...draft,
    ...overrides,
  };
}

function createSampleDraft(overrides?: Partial<RFQDraft>): RFQDraft {
  const draft: RFQDraft = {
    general_info: {
      subject: "RFQ for global launch marketing services for new kids health drink",
      rfq_code: "RFQ-MKT-KIDS-GL-2026-001",
      sourcing_type: "RFQ",
      round: "Round 1",
      status: "Draft",
      owner: "Ava Thompson",
      currency: "USD",
      requestor: "Global Brand Marketing Team",
      department: "Marketing Procurement",
      category: "Marketing Services",
    },
    scope_overview:
      "Appoint an integrated agency partner to launch a kids health drink across creative, production, social, and governance workstreams.",
    timelines: {
      clarifications_deadline: "2026-05-12",
      technical_bid_deadline: "2026-05-19",
      commercial_bid_deadline: "2026-05-21",
      evaluation_start_date: "2026-05-22",
      negotiation_start_date: "2026-05-27",
      final_award_date: "2026-06-02",
    },
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
        linked_schedule_fields: [],
        deterministic_scoring: {
          guide_type: "numeric_banded",
          answer_format: "Comparable launches in last 3 years",
          summary: "Score experience from the number of comparable launches disclosed by the vendor.",
          rules: [
            { id: "rule_experience_1", condition: "5 or more launches", score: 10, outcome: null },
            { id: "rule_experience_2", condition: "3 to 4 launches", score: 8, outcome: null },
            { id: "rule_experience_3", condition: "2 launches", score: 6, outcome: null },
            { id: "rule_experience_4", condition: "0 to 1 launch", score: 0, outcome: null },
          ],
        },
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
        linked_schedule_fields: [],
        deterministic_scoring: null,
        qualitative_scoring_guidance:
          "Judge whether the governance response is specific, implementation-ready, and backed by clear ownership, cadence, and escalation logic.",
      },
      {
        id: "criterion_pricing",
        section_id: "section_commercial",
        title: "Complete pricing response",
        description: "Quotes all applicable line items and states exclusions clearly.",
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
        linked_question_ids: ["question_pricing"],
        linked_schedule_fields: ["schedule_commercial.total_fee"],
        deterministic_scoring: {
          guide_type: "pass_fail",
          answer_format: "Pricing completeness confirmation",
          summary: "Pass if the buyer can clearly tell that all applicable line items are quoted and exclusions are stated.",
          rules: [
            {
              id: "rule_pricing_pass",
              condition: "All applicable line items are quoted and exclusions are stated clearly.",
              score: null,
              outcome: "pass",
            },
            {
              id: "rule_pricing_fail",
              condition: "Any applicable line item is missing or exclusions are unclear.",
              score: null,
              outcome: "fail",
            },
          ],
        },
      },
    ],
    aggregate_technical_threshold: 70,
    questions: [
      {
        id: "question_experience",
        text: "How many comparable nutrition or kids-focused launches have you delivered in the last three years? List them with outcomes.",
        purpose: "Validate relevant launch experience.",
        linked_criteria: ["criterion_experience"],
      },
      {
        id: "question_governance",
        text: "Describe the team structure, reporting cadence, and decision governance.",
        purpose: "Validate execution governance.",
        linked_criteria: ["criterion_governance"],
      },
      {
        id: "question_pricing",
        text: "Confirm that you are quoting all applicable RFQ line items and clearly identify all exclusions or assumptions.",
        purpose: "Validate completeness of the commercial response.",
        linked_criteria: ["criterion_pricing"],
      },
    ],
    response_schedules: [
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
  subject?: string;
  withRubric?: boolean;
  withArtifact?: boolean;
  template?: "blank" | "sample";
}): SessionSnapshot {
  const sessionId = options?.sessionId ?? "session_123";
  const template = options?.template ?? "blank";
  const baseDraft =
    template === "sample"
      ? createSampleDraft({
          general_info: {
            subject: options?.subject ?? "RFQ for global launch marketing services for new kids health drink",
            rfq_code: "RFQ-MKT-KIDS-GL-2026-001",
            sourcing_type: "RFQ",
            round: "Round 1",
            status: "Draft",
            owner: "Ava Thompson",
            currency: "USD",
            requestor: "Global Brand Marketing Team",
            department: "Marketing Procurement",
            category: "Marketing Services",
          },
        })
      : createBlankDraft({
          general_info: {
            subject: options?.subject ?? "",
            rfq_code: "",
            sourcing_type: "",
            round: "",
            status: "",
            owner: "",
            currency: "",
            requestor: "",
            department: "",
            category: "",
          },
        });
  const rfqDraft = baseDraft;
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
    getRfqTemplate: vi.fn(async (templateName: "blank" | "sample") =>
      cloneValue(templateName === "sample" ? createSampleDraft() : createBlankDraft()),
    ),
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
    vi.restoreAllMocks();
    window.sessionStorage.clear();
  });

  it("loads a blank RFQ on first session render", async () => {
    const { api } = createStatefulApi(createSessionSnapshot({ withRubric: false, template: "blank" }));

    render(
      <RfqWizard
        api={api}
        autosaveMs={5}
        onStepChange={vi.fn()}
        sessionId="session_123"
        step="input"
      />,
    );

    expect(await screen.findByText("Use RFQ Sample")).toBeInTheDocument();
    expect(screen.getByLabelText("Subject")).toHaveValue("");
    expect(screen.queryByDisplayValue("Strategy & Creative Development")).not.toBeInTheDocument();
  });

  it("rehydrates a stale session URL instead of hanging on the loading state", async () => {
    const snapshot = createSessionSnapshot({ withRubric: false, template: "blank" });
    const api: RfqApiClient = {
      ...createStatefulApi(snapshot).api,
      getSession: vi.fn(async () => {
        throw new ApiError("Session not found.", 404, "Session not found.");
      }),
      createOrHydrateSession: vi.fn(async () => cloneValue(snapshot)),
    };

    render(
      <RfqWizard
        api={api}
        autosaveMs={5}
        onStepChange={vi.fn()}
        sessionId="session_123"
        step="input"
      />,
    );

    expect(await screen.findByText("Use RFQ Sample")).toBeInTheDocument();
    expect(screen.getByLabelText("Subject")).toHaveValue("");
    expect(api.getSession).toHaveBeenCalledWith("session_123");
    expect(api.createOrHydrateSession).toHaveBeenCalledWith("session_123");
  });

  it("shows exact linked questions and deterministic grading previews in the criterion cards", async () => {
    const { api } = createStatefulApi(createSessionSnapshot());

    render(
      <RfqWizard api={api} autosaveMs={5} onStepChange={vi.fn()} sessionId="session_123" step="proposal" />,
    );

    expect(await screen.findByText("Rubric Governance")).toBeInTheDocument();
    expect(screen.getAllByText("Buyer-facing criterion view").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Criterion summary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Primary vendor question").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Scoring and qualifying rule").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Advanced traceability and evaluator checks").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Scored Criterion with Minimum Qualifying Score").length).toBeGreaterThan(0);
    expect(
      screen.getAllByText(
        "How many comparable nutrition or kids-focused launches have you delivered in the last three years? List them with outcomes.",
      ).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText("5 or more launches")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Confirm that you are quoting all applicable RFQ line items and clearly identify all exclusions or assumptions.",
      ).length,
    ).toBeGreaterThan(0);
    expect(
      screen.getByText("All applicable line items are quoted and exclusions are stated clearly."),
    ).toBeInTheDocument();
    expect(screen.getByText("AI judging guidance")).toBeInTheDocument();
    expect(
      screen.getAllByText(
        "Judge whether the governance response is specific, implementation-ready, and backed by clear ownership, cadence, and escalation logic.",
      ).length,
    ).toBeGreaterThan(0);
  });

  it("keeps buyer RFQ edits across step changes and refresh within the same session", async () => {
    const { api, readSnapshot } = createStatefulApi(createSessionSnapshot({ template: "blank" }));
    const onStepChange = vi.fn();

    const firstRender = render(
      <RfqWizard api={api} autosaveMs={25} onStepChange={onStepChange} sessionId="session_123" step="input" />,
    );

    const subjectInput = await screen.findByLabelText("Subject");
    fireEvent.change(subjectInput, { target: { value: "Edited RFQ Subject" } });

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

    expect(await screen.findByDisplayValue("Edited RFQ Subject")).toBeInTheDocument();
    expect(readSnapshot().rfq_draft.general_info.subject).toBe("Edited RFQ Subject");
  });

  it("loads the full sample RFQ into the session when requested", async () => {
    const { api, readSnapshot } = createStatefulApi(createSessionSnapshot({ withRubric: false, template: "blank" }));

    render(
      <RfqWizard api={api} autosaveMs={25} onStepChange={vi.fn()} sessionId="session_123" step="input" />,
    );

    expect(await screen.findByRole("button", { name: "Use RFQ Sample" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Use RFQ Sample" }));

    expect(await screen.findByDisplayValue("RFQ for global launch marketing services for new kids health drink")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Strategy & Creative Development")).toBeInTheDocument();
    expect(readSnapshot().rfq_draft.buyer_priorities).toHaveLength(2);
    expect(api.getRfqTemplate).toHaveBeenCalledWith("sample");
    expect(api.saveRfq).toHaveBeenCalled();
  });

  it("clears the full RFQ draft back to blank inputs", async () => {
    const { api, readSnapshot } = createStatefulApi(createSessionSnapshot({ withRubric: false, template: "sample" }));

    render(
      <RfqWizard api={api} autosaveMs={25} onStepChange={vi.fn()} sessionId="session_123" step="input" />,
    );

    expect(await screen.findByDisplayValue("RFQ for global launch marketing services for new kids health drink")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Clear RFQ" }));

    expect(await screen.findByLabelText("Subject")).toHaveValue("");
    expect(screen.queryByDisplayValue("Strategy & Creative Development")).not.toBeInTheDocument();
    expect(readSnapshot().rfq_draft.mandatory_conditions).toHaveLength(0);
    expect(api.getRfqTemplate).toHaveBeenCalledWith("blank");
  });

  it("resets to a fresh blank session without mutating the current session", async () => {
    const currentSnapshot = createSessionSnapshot({
      sessionId: "session_current",
      subject: "Changed in current session",
      withArtifact: true,
      template: "sample",
    });
    const freshSnapshot = createSessionSnapshot({
      sessionId: "session_fresh",
      withRubric: false,
      template: "blank",
    });
    const { api } = createStatefulApi(currentSnapshot);
    const onSessionReplace = vi.fn();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    api.createOrHydrateSession = vi.fn(async (requestedSessionId?: string) => {
      expect(requestedSessionId).toBeUndefined();
      return cloneValue(freshSnapshot);
    });

    render(
      <RfqWizard
        api={api}
        autosaveMs={25}
        onSessionReplace={onSessionReplace}
        onStepChange={vi.fn()}
        sessionId="session_current"
        step="lock"
      />,
    );

    expect(await screen.findByText("Lock Review")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Reset session" }));

    await waitFor(() => {
      expect(api.createOrHydrateSession).toHaveBeenCalledWith();
    });

    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onSessionReplace).toHaveBeenCalledWith("session_fresh", "input");
    expect(window.sessionStorage.getItem("rfq-prototype-session-id")).toBe("session_fresh");
    expect(api.saveRfq).not.toHaveBeenCalled();
    expect(api.saveRubric).not.toHaveBeenCalled();
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

    const subjectInput = await screen.findByLabelText("Subject");
    fireEvent.change(subjectInput, { target: { value: "Retry-safe RFQ Subject" } });
    fireEvent.click(screen.getByRole("button", { name: "Generate AI rubric" }));

    expect(await screen.findByText(/Request failed\./)).toBeInTheDocument();
    expect(screen.getByDisplayValue("Retry-safe RFQ Subject")).toBeInTheDocument();
    expect(readSnapshot().rfq_draft.general_info.subject).toBe("Retry-safe RFQ Subject");
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
