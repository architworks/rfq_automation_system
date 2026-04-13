import type {ReactNode} from 'react';
import Link from '@docusaurus/Link';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

const strengths = [
  {
    title: 'Connected framework generation',
    body:
      'TenderLens does not let one AI step invent questions, a second AI step guess at extraction, and a third AI step improvise the scoring logic. The rubric, questions, schedules, and evidence expectations are generated as one connected framework first.',
  },
  {
    title: 'Deterministic gate where it matters',
    body:
      'Technical qualification, commercial comparability, normalization, and the official QCBS 70/30 award basis stay grounded in deterministic logic once the framework is locked.',
  },
  {
    title: 'Evidence-backed explainability',
    body:
      'Every important output is designed to trace back to vendor answers, extracted structured fields, evidence anchors, and explicit scoring or disqualification logic.',
  },
  {
    title: 'Official result vs AI insight',
    body:
      'The product separates one governed official result from advisory AI insights such as QBS, LCS, and contextual scenario analysis.',
  },
];

const assumptions = [
  'Prototype-first delivery focused on proving the RFQ-to-award workflow, not on production multi-user operations.',
  'No authentication, no durable database, and no collaboration features in the current prototype.',
  'One browser session is used as the working unit of state for the demo flow.',
  'The documentation site is written for reviewers evaluating problem framing, architecture, and tradeoffs rather than for end users learning the UI.',
];

const systemSteps = [
  'Buyer defines the RFQ context and locks a framework before vendors are judged.',
  'AI proposes the rubric, questions, schedules, and evidence expectations in one connected generation step.',
  'Vendors submit messy documents and the system extracts structured responses against the locked framework.',
  'Deterministic normalization converts commercial and measurable data into a comparable evaluation basis.',
  'Technical qualification, commercial comparison, official award logic, and advisory AI insights are generated from the same grounded evidence chain.',
];

const improvements = [
  'Move long-running AI work onto durable background jobs instead of synchronous request/response flows.',
  'Add persistent storage for sessions, vendor uploads, extracted evidence, and evaluation reports.',
  'Expand production-grade ingestion for more document edge cases, especially visual-heavy Word, PowerPoint, and spreadsheet submissions.',
  'Add buyer collaboration, review workflows, and audit history around framework edits and award decisions.',
  'Harden observability, evaluation QA, and benchmark datasets for repeated procurement scenarios.',
];

export default function Home(): ReactNode {
  return (
    <Layout
      title="TenderLens"
      description="Submission-first documentation for an AI-assisted RFQ evaluation and award recommendation prototype.">
      <main className={styles.page}>
        <section className={styles.hero}>
          <div className={styles.heroInner}>
            <div className={styles.eyebrow}>Submission Documentation</div>
            <Heading as="h1" className={styles.heroTitle}>
              TenderLens
            </Heading>
            <p className={styles.heroSubtitle}>
              An AI-assisted RFQ evaluation prototype designed to turn messy vendor submissions
              into a defensible, explainable award recommendation.
            </p>
            <div className={styles.heroActions}>
              <Link className="button button--primary button--lg" to="/docs/overview">
                Read the Overview
              </Link>
              <Link className="button button--secondary button--lg" to="/docs/demo-video-script">
                Open the 5-Minute Demo Script
              </Link>
            </div>
            <div className={styles.heroCallout}>
              <strong>Core thesis:</strong> the strongest design choice in TenderLens is that the
              system defines the evaluation framework first, then keeps questionnaire generation,
              extraction, scoring, normalization, and award logic aligned to that same locked
              framework.
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionEyebrow}>Problem Solved</div>
            <Heading as="h2" className={styles.sectionTitle}>
              Procurement teams need more than document summarization
            </Heading>
          </div>
          <div className={styles.problemGrid}>
            <article className={styles.problemCard}>
              <Heading as="h3" className={styles.cardTitle}>
                The real bottleneck
              </Heading>
              <p>
                Buyers receive non-standard proposals across PDF, Word, PowerPoint, and spreadsheet
                formats. Pricing, scope coverage, compliance statements, and delivery details are
                scattered across narrative sections and tables.
              </p>
            </article>
            <article className={styles.problemCard}>
              <Heading as="h3" className={styles.cardTitle}>
                Why a generic LLM flow is weak
              </Heading>
              <p>
                If question generation, extraction, and scoring are disconnected AI calls, the
                system becomes subjective and hard to audit. The evaluator cannot tell whether the
                model is judging vendors against a stable framework or simply reacting to raw text.
              </p>
            </article>
            <article className={styles.problemCard}>
              <Heading as="h3" className={styles.cardTitle}>
                What this prototype proves
              </Heading>
              <p>
                TenderLens shows how an AI-assisted procurement system can generate a strong RFQ
                framework first, then use that locked structure to drive extraction, normalization,
                evaluation, evidence capture, and award explainability.
              </p>
            </article>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionEyebrow}>Key Strengths</div>
            <Heading as="h2" className={styles.sectionTitle}>
              What makes TenderLens different
            </Heading>
          </div>
          <div className={styles.cardGrid}>
            {strengths.map((item) => (
              <article className={styles.infoCard} key={item.title}>
                <Heading as="h3" className={styles.cardTitle}>
                  {item.title}
                </Heading>
                <p>{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.twoCol}>
            <div>
              <div className={styles.sectionEyebrow}>Assumptions</div>
              <Heading as="h2" className={styles.sectionTitle}>
                Current prototype boundaries
              </Heading>
              <ul className={styles.list}>
                {assumptions.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className={styles.sectionEyebrow}>System Design</div>
              <Heading as="h2" className={styles.sectionTitle}>
                High-level flow
              </Heading>
              <ol className={styles.stepList}>
                {systemSteps.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
            </div>
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionEyebrow}>Future Work</div>
            <Heading as="h2" className={styles.sectionTitle}>
              What I would improve with more time
            </Heading>
          </div>
          <div className={styles.cardGrid}>
            {improvements.map((item) => (
              <article className={styles.infoCard} key={item}>
                <p>{item}</p>
              </article>
            ))}
          </div>
        </section>

        <section className={styles.ctaSection}>
          <Heading as="h2" className={styles.ctaTitle}>
            Continue through the submission
          </Heading>
          <p className={styles.ctaText}>
            Start with the evaluator-facing overview, then move into the evaluation logic, system
            flow, and technical appendix.
          </p>
          <div className={styles.heroActions}>
            <Link className="button button--primary button--lg" to="/docs/overview">
              Overview
            </Link>
            <Link className="button button--secondary button--lg" to="/docs/technical-appendix/implementation-pipeline">
              Technical Appendix
            </Link>
          </div>
        </section>
      </main>
    </Layout>
  );
}
