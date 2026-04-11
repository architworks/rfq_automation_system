import type { ArtifactDownload, LockedFrameworkArtifact, VendorPack } from "@/lib/api";

function sanitizeFileNamePart(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

function buildFileName(artifact: LockedFrameworkArtifact): string {
  const seed = artifact.rfq_snapshot.general_info.rfq_code || artifact.rfq_snapshot.general_info.subject || "vendor-rfq";
  const base = sanitizeFileNamePart(seed) || "vendor-rfq";
  return `${base}-vendor-pack.docx`;
}

export async function buildVendorPackDocument(
  artifact: LockedFrameworkArtifact,
  vendorPack: VendorPack,
): Promise<ArtifactDownload> {
  const docx = await import("docx");
  const {
    AlignmentType,
    BorderStyle,
    Document,
    HeadingLevel,
    Packer,
    Paragraph,
    Table,
    TableCell,
    TableRow,
    TextRun,
    WidthType,
  } = docx;

  const cell = (text: string, bold = false) =>
    new TableCell({
      width: {
        size: 25,
        type: WidthType.PERCENTAGE,
      },
      children: [
        new Paragraph({
          children: [
            new TextRun({
              text,
              bold,
            }),
          ],
        }),
      ],
    });

  const fullWidthTable = (rows: InstanceType<typeof TableRow>[]) =>
    new Table({
      width: {
        size: 100,
        type: WidthType.PERCENTAGE,
      },
      borders: {
        top: { style: BorderStyle.SINGLE, size: 1, color: "B8C0CC" },
        bottom: { style: BorderStyle.SINGLE, size: 1, color: "B8C0CC" },
        left: { style: BorderStyle.SINGLE, size: 1, color: "B8C0CC" },
        right: { style: BorderStyle.SINGLE, size: 1, color: "B8C0CC" },
        insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "D6DCE5" },
        insideVertical: { style: BorderStyle.SINGLE, size: 1, color: "D6DCE5" },
      },
      rows,
    });

  const bulletParagraphs = (items: string[]) =>
    items.map(
      (item) =>
        new Paragraph({
          text: item,
          bullet: {
            level: 0,
          },
        }),
    );

  const title = artifact.rfq_snapshot.general_info.subject;
  const generalInfo = artifact.rfq_snapshot.general_info;
  const timelines = artifact.rfq_snapshot.timelines;
  const mandatoryConditions = artifact.rfq_snapshot.mandatory_conditions ?? [];
  const lineItems = artifact.rfq_snapshot.line_items ?? [];
  const responseInstructions = vendorPack.response_instructions ?? [];
  const questions = vendorPack.questions ?? [];
  const schedules = vendorPack.response_schedules ?? [];

  const children = [
    new Paragraph({
      text: title,
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
    }),
    new Paragraph({
      text: "Vendor Response Pack",
      alignment: AlignmentType.CENTER,
    }),
    new Paragraph({ text: "" }),
    fullWidthTable([
      new TableRow({
        children: [cell("RFQ Code", true), cell(generalInfo.rfq_code), cell("Sourcing Type", true), cell(generalInfo.sourcing_type)],
      }),
      new TableRow({
        children: [cell("Round", true), cell(generalInfo.round), cell("Status", true), cell(generalInfo.status)],
      }),
      new TableRow({
        children: [cell("Owner", true), cell(generalInfo.owner), cell("Currency", true), cell(generalInfo.currency)],
      }),
      new TableRow({
        children: [cell("Requestor", true), cell(generalInfo.requestor), cell("Department", true), cell(generalInfo.department)],
      }),
      new TableRow({
        children: [cell("Category", true), cell(generalInfo.category), cell("Submission Format", true), cell("One complete response document")],
      }),
    ]),
    new Paragraph({ text: "" }),
    new Paragraph({
      text: "Scope Overview",
      heading: HeadingLevel.HEADING_1,
    }),
    new Paragraph({
      text: artifact.rfq_snapshot.scope_overview,
    }),
    new Paragraph({
      text: "Key Timelines",
      heading: HeadingLevel.HEADING_1,
    }),
    ...bulletParagraphs(
      [
        `Clarifications deadline: ${timelines.clarifications_deadline}`,
        `Technical bid deadline: ${timelines.technical_bid_deadline}`,
        `Commercial bid deadline: ${timelines.commercial_bid_deadline}`,
        `Evaluation start date: ${timelines.evaluation_start_date}`,
        `Negotiation start date: ${timelines.negotiation_start_date}`,
        `Final award date: ${timelines.final_award_date}`,
      ],
    ),
    new Paragraph({
      text: "Mandatory Conditions",
      heading: HeadingLevel.HEADING_1,
    }),
    ...bulletParagraphs(mandatoryConditions),
    new Paragraph({
      text: "Requested Line Items",
      heading: HeadingLevel.HEADING_1,
    }),
    fullWidthTable([
      new TableRow({
        children: [
          cell("Item", true),
          cell("Category", true),
          cell("UOM", true),
          cell("Description", true),
        ],
      }),
      ...lineItems.map(
        (lineItem) =>
          new TableRow({
            children: [
              cell(`${lineItem.product_name} (${lineItem.id})`),
              cell(lineItem.category),
              cell(lineItem.uom),
              cell(lineItem.description),
            ],
          }),
      ),
    ]),
    new Paragraph({ text: "" }),
    new Paragraph({
      text: "Response Instructions",
      heading: HeadingLevel.HEADING_1,
    }),
    ...bulletParagraphs(responseInstructions),
    new Paragraph({
      text: "Vendor Questionnaire",
      heading: HeadingLevel.HEADING_1,
    }),
    ...questions.flatMap((question) => [
      new Paragraph({
        children: [
          new TextRun({
            text: `${question.id.toUpperCase()}. `,
            bold: true,
          }),
          new TextRun(question.text),
        ],
      }),
      new Paragraph({ text: "" }),
    ]),
    new Paragraph({
      text: "Response Schedules",
      heading: HeadingLevel.HEADING_1,
    }),
    ...schedules.flatMap((schedule) => [
      new Paragraph({
        text: `${schedule.name} (${schedule.id})`,
        heading: HeadingLevel.HEADING_2,
      }),
      new Paragraph({
        text: schedule.purpose,
      }),
      fullWidthTable([
        new TableRow({
          children: [
            cell("Field", true),
            cell("Label", true),
            cell("Description", true),
            cell("Required", true),
          ],
        }),
        ...(schedule.columns ?? []).map(
          (column) =>
            new TableRow({
              children: [
                cell(column.field_id),
                cell(column.label),
                cell(column.description),
                cell(column.required ? "Yes" : "No"),
              ],
            }),
        ),
      ]),
      new Paragraph({ text: "" }),
    ]),
  ];

  const document = new Document({
    sections: [
      {
        properties: {},
        children,
      },
    ],
  });

  return {
    blob: await Packer.toBlob(document),
    fileName: buildFileName(artifact),
  };
}
