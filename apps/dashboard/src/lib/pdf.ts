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

function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function isPdf(bytes: Uint8Array): boolean {
  return bytes.length >= 5 && bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46;
}

function downloadFile(file: File): void {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 120_000);
}

function showPreview(preview: Window, file: File): void {
  const url = URL.createObjectURL(file);
  const title = escapeHtml(file.name);
  preview.document.open();
  preview.document.write(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <style>
    html, body { margin: 0; height: 100%; background: #0f172a; }
    .bar { display:flex; gap:12px; align-items:center; padding:8px 12px;
           font: 13px/1.4 sans-serif; background:#1e293b; color:#e2e8f0; }
    .bar a { color:#7dd3fc; }
    iframe { border: 0; width: 100%; height: calc(100% - 36px); }
  </style>
</head>
<body>
  <div class="bar"><a href="${url}" download="${title}">Download PDF</a></div>
  <iframe src="${url}" title="${title}"></iframe>
</body>
</html>`);
  preview.document.close();
  const revoke = () => URL.revokeObjectURL(url);
  preview.addEventListener("beforeunload", revoke);
}

export async function exportPdf(report: PdfReport): Promise<void> {
  const filename = `${slug(report.title)}.pdf`;
  // Open while we still have the click gesture. Chrome cannot render a raw
  // blob: URL in its PDF viewer, so this tab becomes an HTML wrapper instead.
  const preview = window.open("about:blank", "_blank");
  if (preview?.document?.body) {
    preview.document.title = filename;
    preview.document.body.innerHTML = "<p style='font:14px sans-serif;padding:24px'>Preparing PDF…</p>";
  }

  try {
    const response = await fetch(`${API_BASE}/api/exports/pdf`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", Accept: "application/pdf" },
      body: JSON.stringify(report),
    });
    if (!response.ok) {
      throw new ApiError(response.status, `Request failed: ${response.status}`);
    }
    const bytes = new Uint8Array(await response.arrayBuffer());
    if (!isPdf(bytes)) {
      throw new ApiError(response.status, "Server did not return a PDF");
    }
    const file = new File([bytes], filename, { type: "application/pdf" });
    downloadFile(file);
    if (preview && !preview.closed) {
      showPreview(preview, file);
    }
  } catch (error) {
    preview?.close();
    throw error;
  }
}
