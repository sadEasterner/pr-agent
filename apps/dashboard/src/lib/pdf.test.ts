/// <reference types="vitest/globals" />
import { afterEach, describe, expect, it, vi } from "vitest";
import { exportPdf } from "./pdf";

describe("exportPdf", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("downloads a PDF without opening a blob tab", async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const fetchMock = vi.fn(
      async () =>
        new Response("%PDF-1.3\n%%EOF\n", {
          status: 200,
          headers: { "Content-Type": "application/pdf" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("open", vi.fn());
    vi.stubGlobal("URL", {
      ...URL,
      createObjectURL: vi.fn(() => "blob:http://localhost/pdf"),
      revokeObjectURL: vi.fn(),
    });

    await exportPdf({ title: "People", tables: [{ headers: ["Name"], rows: [[null as unknown as string]] }] });

    expect(window.open).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalled();
    expect(click).toHaveBeenCalled();
  });

  it("rejects non-PDF responses", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>nope</html>", { status: 200 })));
    await expect(exportPdf({ title: "Overview" })).rejects.toThrow("Server did not return a PDF");
  });
});
