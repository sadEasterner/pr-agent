import { API_BASE, ApiError } from "../api";

export type PdfMetric = { label: string; value: string | number };
export type PdfTable = { title?: string; headers: string[]; rows: Array<Array<string | number>> };

export type PdfReport = {
  title: string;
  subtitle?: string;
  metrics?: PdfMetric[];
  tables?: PdfTable[];
  notes?: string[];
};

function slug(title: string): string {
  const value = title.replace(/[^\w]+/g, "-").replace(/^-|-$/g, "");
  return (value || "report").slice(0, 80);
}

export async function exportPdf(report: PdfReport): Promise<void> {
  const response = await fetch(`${API_BASE}/api/exports/pdf`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(report),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }
  const blob = new Blob([await response.arrayBuffer()], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const filename = `${slug(report.title)}.pdf`;
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.open(url, "_blank");
  window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
