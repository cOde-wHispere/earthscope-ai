import { AlertCircle, Database, LoaderCircle } from "lucide-react";
import type { ApiError } from "../api/client";

export function LoadingState() {
  return (
    <div className="state loading-state" role="status">
      <LoaderCircle className="spin" size={28} />
      <h2>Loading the scientific record</h2>
      <p>
        Checking source metadata and requesting the validated backend results.
      </p>
    </div>
  );
}
export function ErrorState({
  error,
  title = "Data unavailable",
}: {
  error: ApiError;
  title?: string;
}) {
  return (
    <div className="state error-state" role="alert">
      <AlertCircle size={24} />
      <h3>{title}</h3>
      <p>{error.message}</p>
      <code>{error.code}</code>
    </div>
  );
}
export function EmptyState({ label = "this view" }: { label?: string }) {
  return (
    <div className="state">
      <Database size={26} />
      <h3>No observations available</h3>
      <p>
        The service returned no observations for {label}. No values have been
        substituted.
      </p>
    </div>
  );
}
