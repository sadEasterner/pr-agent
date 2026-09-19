/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from "vitest";
import { exportPdf } from "./pdf";

describe("exportPdf", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("previews the PDF in an HTML tab instead of opening the blob directly", async () => {
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const previewDoc = {
      title: "",
      body: { innerHTML: "" },
      open: vi.fn(),
      write: vi.fn(),
      close: vi.fn(),
    };
    const preview = {
      closed: false,
      document: previewDoc,
      addEventListener: vi.fn(),
      close: vi.fn(),
    };
    const open = vi.fn(() => preview);
    const fetchMock = vi.fn(
      async () =>
        new Response("%PDF-1.3\n%%EOF\n", {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        }),
    );
    vi.stubGlobal("open", open);
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:http://localhost/pdf"),
      revokeObjectURL: vi.fn(),
    });

    await exportPdf({ title: "Overview" });

    expect(open).toHaveBeenCalledWith("about:blank", "_blank");
    expect(fetchMock).toHaveBeenCalled();
    expect(previewDoc.write).toHaveBeenCalled();
    const html = String(previewDoc.write.mock.calls[0][0]);
    expect(html).toContain("<iframe");
    expect(html).toContain('src="blob:http://localhost/pdf"');
    expect(html).toContain("Download PDF");
    expect(open.mock.invocationCallOrder[0]).toBeLessThan(fetchMock.mock.invocationCallOrder[0]);
  });

  it("rejects non-PDF responses", async () => {
    const preview = {
      closed: false,
      document: { title: "", body: { innerHTML: "" }, open: vi.fn(), write: vi.fn(), close: vi.fn() },
      addEventListener: vi.fn(),
      close: vi.fn(),
    };
    vi.stubGlobal("open", vi.fn(() => preview));
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>nope</html>", { status: 200 })));

    await expect(exportPdf({ title: "Overview" })).rejects.toThrow("Server did not return a PDF");
    expect(preview.close).toHaveBeenCalled();
    expect(preview.document.write).not.toHaveBeenCalled();
  });
});
