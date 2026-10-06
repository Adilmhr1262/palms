import React from "react";

export function Field({
  label,
  htmlFor,
  children,
  hint,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="mb-4">
      <label className="field-label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

type InputProps = React.InputHTMLAttributes<HTMLInputElement>;

export function TextInput(props: InputProps) {
  return <input {...props} className={`field-input ${props.className || ""}`} />;
}

export function NumberInput(props: InputProps) {
  return (
    <input
      type="number"
      {...props}
      className={`field-input ${props.className || ""}`}
    />
  );
}

export function CheckboxInput({
  label,
  ...props
}: { label: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" {...props} className="h-4 w-4 accent-[#2b2b2b]" />
      {label}
    </label>
  );
}

type TextAreaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

export function TextArea(props: TextAreaProps) {
  return (
    <textarea
      {...props}
      className={`field-input min-h-[96px] ${props.className || ""}`}
    />
  );
}

type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement>;

export function SelectInput(props: SelectProps) {
  return (
    <select {...props} className={`field-input ${props.className || ""}`} />
  );
}

export function FormError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p className="mb-4 rounded border border-alert/30 bg-[#f9e9e6] px-3 py-2 text-sm text-alert">
      {message}
    </p>
  );
}
