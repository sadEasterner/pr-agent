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

function isPdf(bytes: Uint8Array): boolean {
  return bytes.length >= 5 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
}

function downloadPdf(bytes: Uint8Array, filename: string): void {
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  const blob = new Blob([copy], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000);
}

export async function exportPdf(report: PdfReport): Promise<void> {
  const filename = `${slug(report.title)}.pdf`;
  const response = await fetch(`${API_BASE}/api/exports/pdf`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "application/pdf" },
    body: JSON.stringify(report, (_key, value) => (value == null ? "" : value)),
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!isPdf(bytes)) {
    throw new ApiError(response.status, "Server did not return a PDF");
  }
  downloadPdf(bytes, filename);
}
