import { describe, expect, it } from "vitest";
import { SpeakerInfoFromJSON } from "@/openapi/models/SpeakerInfo";

describe("speaker portrait credit", () => {
  it("preserves short attribution separately from the full policy", () => {
    const info = SpeakerInfoFromJSON({
      policy: "音声データのクレジット\n禁止事項の全文",
      credit: "イラスト素材：花兎*様",
      portrait: "",
      style_infos: [],
    });
    expect(info.credit).toBe("イラスト素材：花兎*様");
    expect(info.policy).toContain("禁止事項の全文");
  });

  it("does not use policy as portrait credit for engines without credits", () => {
    const info = SpeakerInfoFromJSON({
      policy: "長い利用規約",
      portrait: "",
      style_infos: [],
    });
    expect(info.credit).toBeUndefined();
    expect(info.policy).toBe("長い利用規約");
  });
});
