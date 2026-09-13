import { describe, expect, it } from "vitest";
import { createVolumeEnvelope, MouthGate } from "@/helpers/portraitLipSync";

describe("portrait lip sync", () => {
  it("keeps silence and quiet noise closed, and releases after speech", () => {
    const gate = new MouthGate();
    expect(gate.update(0, 0)).toBe(false);
    expect(gate.update(0.003, 40)).toBe(false);
    expect(gate.update(0.1, 80)).toBe(true);
    expect(gate.update(0, 120)).toBe(true);
    expect(gate.update(0, 160)).toBe(false);
  });

  it("avoids chatter around the opening threshold", () => {
    const gate = new MouthGate();
    expect(gate.update(0.02, 0)).toBe(true);
    expect(gate.update(0.01, 120)).toBe(true);
    expect(gate.update(0, 200)).toBe(false);
    expect(gate.update(0.01, 240)).toBe(false);
  });

  it("preserves silence, opposite-phase stereo and the final partial frame", () => {
    const channels = [
      new Float32Array([0, 0, 0.5, -0.5, 0.25]),
      new Float32Array([0, 0, -0.5, 0.5, -0.25]),
    ];
    const audio = {
      sampleRate: 100,
      length: 5,
      numberOfChannels: 2,
      getChannelData: (channel: number) => channels[channel],
    } as AudioBuffer;
    expect([...createVolumeEnvelope(audio)]).toEqual([0, 0.5, 0.25]);
  });
});
