import { afterEach, describe, expect, it, vi } from "vitest";
import { base64ImageToUri } from "@/helpers/base64Helper";

describe("base64ImageToUri", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it.each([
    ["jpeg", "/w==", "image/jpeg"],
    ["gif", "R0E=", "image/gif"],
    ["png", "iVBORw==", "image/png"],
    ["webp", "UklGRg==", "image/webp"],
    ["SVG with XML declaration", "PD94bWwgdmVyc2lvbj0iMS4wIj8+", "image/svg+xml"],
    ["SVG tag", "PHN2Zy8+", "image/svg+xml"],
  ])("detects %s resources", async (_label, data, mimeType) => {
    const createObjectURL = vi.fn((_: Blob) => "blob:test");
    vi.stubGlobal("URL", { createObjectURL });

    await base64ImageToUri(data);

    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(createObjectURL.mock.calls[0][0]).toBeInstanceOf(Blob);
    expect((createObjectURL.mock.calls[0][0] as Blob).type).toBe(mimeType);
  });
});
