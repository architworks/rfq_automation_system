"use client";

import { useId, type ComponentPropsWithoutRef } from "react";

function createFieldIdentity(
  prefix: string,
  providedId: string | undefined,
  providedName: string | undefined,
  generatedId: string,
) {
  const normalizedSuffix = generatedId.replace(/[^a-zA-Z0-9_-]+/g, "");
  const id = providedId ?? `${prefix}-${normalizedSuffix}`;
  const name = providedName ?? id;

  return { id, name };
}

export function FormInput(props: ComponentPropsWithoutRef<"input">) {
  const generatedId = useId();
  const { id: providedId, name: providedName, ...rest } = props;
  const { id, name } = createFieldIdentity("input", providedId, providedName, generatedId);

  return <input {...rest} id={id} name={name} />;
}

export function FormSelect(props: ComponentPropsWithoutRef<"select">) {
  const generatedId = useId();
  const { id: providedId, name: providedName, ...rest } = props;
  const { id, name } = createFieldIdentity("select", providedId, providedName, generatedId);

  return <select {...rest} id={id} name={name} />;
}

export function FormTextarea(props: ComponentPropsWithoutRef<"textarea">) {
  const generatedId = useId();
  const { id: providedId, name: providedName, ...rest } = props;
  const { id, name } = createFieldIdentity("textarea", providedId, providedName, generatedId);

  return <textarea {...rest} id={id} name={name} />;
}
