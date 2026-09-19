export type PdfMetric = { label: string; value: string | number };
export type PdfTable = { title?: string; headers: string[]; rows: Array<Array<string | number>> };

export type PdfReport = {
  title: string;
  subtitle?: string;
  metrics?: PdfMetric[];
  tables?: PdfTable[];
  notes?: string[];
};

function escapeHtml(value: string | number): string {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function buildHtml(report: PdfReport): string {
  const metrics = (report.metrics ?? [])
    .map(
      (item) =>
        `<div class="metric"><span>${escapeHtml(item.label)}</span><strong>${escapeHtml(item.value)}</strong></div>`,
    )
    .join("");
  const tables = (report.tables ?? [])
    .map((table) => {
      const head = table.headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("");
      const body = table.rows
        .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join("")}</tr>`)
        .join("");
      const empty = table.rows.length ? "" : `<tr><td colspan="${Math.max(table.headers.length, 1)}">No rows</td></tr>`;
      return `<section>${table.title ? `<h2>${escapeHtml(table.title)}</h2>` : ""}<table><thead><tr>${head}</tr></thead><tbody>${body}${empty}</tbody></table></section>`;
    })
    .join("");
  const notes = (report.notes ?? []).map((note) => `<li>${escapeHtml(note)}</li>`).join("");
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(report.title)}</title>
  <style>
    body { font-family: "Segoe UI", sans-serif; color: #0f172a; margin: 32px; }
    h1 { font-size: 22px; margin: 0 0 6px; }
    .sub { color: #64748b; margin-bottom: 24px; }
    .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 24px; }
    .metric { border: 1px solid #e2e8f0; border-radius: 12px; padding: 12px; }
    .metric span { display: block; color: #64748b; font-size: 12px; }
    .metric strong { font-size: 18px; }
    table { width: 100%; border-collapse: collapse; margin: 12px 0 24px; font-size: 12px; }
    th, td { border-bottom: 1px solid #e2e8f0; text-align: left; padding: 8px; vertical-align: top; }
    th { color: #64748b; font-weight: 600; }
    h2 { font-size: 15px; margin: 0; }
  </style>
</head>
<body>
  <h1>${escapeHtml(report.title)}</h1>
  ${report.subtitle ? `<p class="sub">${escapeHtml(report.subtitle)}</p>` : ""}
  ${metrics ? `<div class="metrics">${metrics}</div>` : ""}
  ${tables}
  ${notes ? `<ul>${notes}</ul>` : ""}
</body>
</html>`;
}

export function exportPdf(report: PdfReport): void {
  const popup = window.open("", "_blank", "noopener,noreferrer,width=960,height=720");
  if (!popup) {
    window.alert("Allow pop-ups to export a PDF.");
    return;
  }
  popup.document.open();
  popup.document.write(buildHtml(report));
  popup.document.close();
  popup.focus();
  const print = () => popup.print();
  popup.addEventListener("load", print, { once: true });
  window.setTimeout(print, 400);
}
