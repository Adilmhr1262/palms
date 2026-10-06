"use client";

import { useState } from "react";

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Delete",
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
      <div className="w-full max-w-sm rounded border border-line bg-paper p-6">
        <h2 className="text-base font-semibold">{title}</h2>
        <p className="mt-2 text-sm text-muted">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" className="btn-secondary" onClick={onCancel}>
            Cancel
          </button>
          <button type="button" className="btn-primary" onClick={onConfirm}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

export function useConfirm() {
  const [state, setState] = useState<{
    title: string;
    message: string;
    confirmLabel: string;
    action: () => void;
  } | null>(null);
  const ask = (
    title: string,
    message: string,
    action: () => void,
    confirmLabel: string = "Delete"
  ) => setState({ title, message, action, confirmLabel });
  const dialog = (
    <ConfirmDialog
      open={state !== null}
      title={state?.title || ""}
      message={state?.message || ""}
      confirmLabel={state?.confirmLabel || "Delete"}
      onCancel={() => setState(null)}
      onConfirm={() => {
        state?.action();
        setState(null);
      }}
    />
  );
  return { ask, dialog };
}
