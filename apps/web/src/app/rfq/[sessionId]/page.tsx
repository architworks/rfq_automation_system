"use client";

import { useEffect, useTransition } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";

import { RfqWizard, type WizardStep } from "@/components/rfq-wizard/rfq-wizard";
import { setStoredSessionId } from "@/lib/session";

const VALID_STEPS: WizardStep[] = ["input", "proposal", "lock", "pack", "vendors", "review", "results"];

function coerceStep(step: string | null): WizardStep {
  return VALID_STEPS.includes(step as WizardStep) ? (step as WizardStep) : "input";
}

export default function RfqSessionPage() {
  const params = useParams<{ sessionId: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [, startTransition] = useTransition();

  const sessionId = params.sessionId;
  const step = coerceStep(searchParams.get("step"));

  useEffect(() => {
    setStoredSessionId(sessionId);
  }, [sessionId]);

  return (
    <RfqWizard
      sessionId={sessionId}
      step={step}
      onStepChange={(nextStep) => {
        startTransition(() => {
          router.replace(`/rfq/${sessionId}?step=${nextStep}`);
        });
      }}
    />
  );
}
