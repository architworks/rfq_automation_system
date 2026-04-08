"use client";

import { useEffect, useState, useTransition } from "react";
import { useRouter } from "next/navigation";

import { apiClient } from "@/lib/api";
import { clearStoredSessionId, getStoredSessionId, setStoredSessionId } from "@/lib/session";

import styles from "@/components/rfq-wizard/rfq-wizard.module.css";

export default function HomePage() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [message, setMessage] = useState("Creating your RFQ session...");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        const storedSessionId = getStoredSessionId() ?? undefined;
        const session = await apiClient.createOrHydrateSession(storedSessionId);
        if (cancelled) {
          return;
        }

        setStoredSessionId(session.session_id);
        startTransition(() => {
          router.replace(`/rfq/${session.session_id}?step=input`);
        });
      } catch (bootstrapError) {
        if (!cancelled) {
          setError(
            bootstrapError instanceof Error
              ? bootstrapError.message
              : "Failed to bootstrap the RFQ session.",
          );
          setMessage("Session startup failed.");
        }
      }
    }

    void bootstrap();

    return () => {
      cancelled = true;
    };
  }, [router, startTransition]);

  return (
    <div className={styles.shell}>
      <div className={styles.frame}>
        <header className={styles.hero}>
          <div className={styles.eyebrow}>RFQ Prototype</div>
          <h1 className={styles.title}>Bootstrapping Session</h1>
          <p className={styles.subtitle}>
            The prototype uses browser-session ownership with in-memory backend state. A new or
            existing session will be attached automatically.
          </p>
        </header>

        <div className={`${styles.banner} ${error ? styles.errorBanner : styles.infoBanner}`}>
          <strong>{message}</strong>
          {error ? ` ${error}` : isPending ? " Redirecting..." : ""}
        </div>

        {error ? (
          <div className={styles.buttonGroup}>
            <button
              className={styles.secondaryButton}
              onClick={() => {
                clearStoredSessionId();
                window.location.reload();
              }}
              type="button"
            >
              Start with a fresh session
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
