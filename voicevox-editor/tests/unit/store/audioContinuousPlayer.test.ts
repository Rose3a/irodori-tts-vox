import { describe, expect, it, vi } from "vitest";
import type { AudioKey } from "@/type/preload";
import {
  ContinuousPlayer,
  filterNonEmptyAudioKeys,
} from "@/store/audioContinuousPlayer";

describe("audioContinuousPlayer", () => {
  it("filters whitespace-only audio lines before continuous generation", () => {
    expect(
      filterNonEmptyAudioKeys(["blank", "speech", "spaces"], {
        blank: { text: "" },
        speech: { text: "  こんにちは  " },
        spaces: { text: "\n\t" },
      }),
    ).toEqual(["speech"]);
  });

  it("resolves when a line fails instead of waiting forever", async () => {
    const player = new ContinuousPlayer(["speech" as AudioKey], {
      generateAudio: vi.fn().mockRejectedValue(new Error("empty text")),
      playAudioBlob: vi.fn(),
    });

    await expect(player.playUntilComplete()).resolves.toBeUndefined();
  });

  it("continues with later lines after a generation error", async () => {
    const generateAudio = vi
      .fn()
      .mockRejectedValueOnce(new Error("one line failed"))
      .mockResolvedValueOnce(new Blob(["audio"]));
    const playAudioBlob = vi.fn().mockResolvedValue(true);
    const player = new ContinuousPlayer(
      ["first", "second"] as AudioKey[],
      { generateAudio, playAudioBlob },
    );

    await expect(player.playUntilComplete()).resolves.toBeUndefined();
    expect(generateAudio).toHaveBeenCalledTimes(2);
    expect(playAudioBlob).toHaveBeenCalledTimes(1);
  });
});