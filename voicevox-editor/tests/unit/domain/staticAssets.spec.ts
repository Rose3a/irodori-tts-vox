import { describe, expect, test } from "vitest";
import { loadOssLicenses } from "@/domain/staticAssets";

describe("Help license inventory", () => {
  test("includes models, transitive frontend dependencies and Python notices", async () => {
    const licenses = await loadOssLicenses();
    const asr = licenses.find((item) => item.name.includes("口パク ASR"));
    expect(asr?.license).toBe("CC BY 4.0");
    expect(asr?.text).toContain("NVIDIA");
    expect(asr?.text).toContain("int8");
    for (const name of [
      "@vue/shared",
      "sherpa-onnx",
      "dacvae",
      "7-Zip",
    ]) {
      expect(
        licenses.find((item) => item.name === name)?.text.length,
      ).toBeGreaterThan(100);
    }
    expect(licenses.find((item) => item.name === "dacvae")?.license).toBe(
      "Apache-2.0",
    );
    expect(licenses.every((item) => item.text.trim().length > 0)).toBe(true);
  });
});
