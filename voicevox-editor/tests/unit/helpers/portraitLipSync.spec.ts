import { describe, expect, it } from "vitest";
import {
  BlinkScheduler,
  LipSyncDriver,
  LIP_SYNC_SPEED_PRESETS,
  flapWindows,
  inSpans,
  moraTimeline,
  moraTimelineFromAnchors,
  resolveLipSyncOptions,
  speechSpans,
  vowelAt,
  vowelOf,
} from "@/helpers/portraitLipSync";

describe("vowelOf", () => {
  it("ひらがな・カタカナの母音を返す", () => {
    expect(vowelOf("あ")).toBe("a");
    expect(vowelOf("キ")).toBe("i");
    expect(vowelOf("す")).toBe("u");
    expect(vowelOf("ネ")).toBe("e");
    expect(vowelOf("を")).toBe("o");
  });

  it("ん と っ は口を閉じる扱いにする", () => {
    expect(vowelOf("ん")).toBe("n");
    expect(vowelOf("っ")).toBe("n");
    expect(vowelOf("ン")).toBe("n");
  });

  it("母音を持たない文字は undefined", () => {
    expect(vowelOf("、")).toBeUndefined();
    expect(vowelOf("A")).toBeUndefined();
  });
});

describe("moraTimeline", () => {
  it("音声長をモーラ数で比例配分する", () => {
    const steps = moraTimeline("あいうえお", 1.0);
    expect(steps).toHaveLength(5);
    expect(steps[0].start).toBe(0);
    expect(steps[4].end).toBeCloseTo(1.0, 3);
    expect(steps[0].vowel).toBe("a");
    expect(steps[4].vowel).toBe("o");
    for (let i = 1; i < steps.length; i++) {
      expect(steps[i].start).toBeCloseTo(steps[i - 1].end, 4);
    }
  });

  it("拗音・長音符・促音を前後のモーラへ畳む", () => {
    const steps = moraTimeline("きゃーっ", 1.0);
    expect(steps.map((s) => s.vowel)).toEqual(["a", "n"]);
    expect(steps[0].end - steps[0].start).toBeGreaterThan(
      steps[1].end - steps[1].start,
    );
  });

  it("句読点は口を閉じた区間になる", () => {
    const steps = moraTimeline("あ、い", 1.0);
    expect(steps.map((s) => s.vowel)).toEqual(["a", "n", "i"]);
  });

  it("空文字や0秒では空のタイムラインを返す", () => {
    expect(moraTimeline("", 1.0)).toHaveLength(0);
    expect(moraTimeline("あい", 0)).toHaveLength(0);
  });
});

describe("vowelAt", () => {
  it("時刻から現在の母音を引ける", () => {
    const steps = moraTimeline("あいう", 3);
    expect(vowelAt(steps, 0.1)).toBe("a");
    expect(vowelAt(steps, 1.5)).toBe("i");
    expect(vowelAt(steps, 2.9)).toBe("u");
  });

  it("範囲外は undefined", () => {
    const steps = moraTimeline("あい", 1);
    expect(vowelAt(steps, -0.1)).toBeUndefined();
    expect(vowelAt(steps, 2)).toBeUndefined();
    expect(vowelAt([], 0.5)).toBeUndefined();
  });
});

describe("LipSyncDriver", () => {
  const options = resolveLipSyncOptions({
    mode: "vowel",
    speed: "normal",
    blink: "off",
  });

  it("口パクなしのときは常に閉じている", () => {
    const driver = new LipSyncDriver(
      resolveLipSyncOptions({ mode: "off", speed: "fast", blink: "off" }),
      moraTimeline("あいう", 3),
    );
    const frame = driver.update(0.5, 0.1, 0);
    expect(frame).toEqual({ shape: "n", open: false });
  });

  it("簡易モードもタイムラインの窓で開閉する", () => {
    const driver = new LipSyncDriver(
      resolveLipSyncOptions({ mode: "simple", speed: "fast", blink: "off" }),
      moraTimeline("あいう", 3),
    );
    // 窓の中でもレベルが床(closeThreshold)未満なら開かない
    expect(driver.update(0.0001, 0.1, 0).open).toBe(false);
    expect(driver.update(0.4, 0.1, 100)).toEqual({ shape: "a", open: true });
    // モーラの切れ目（閉じている時間）では閉じる
    expect(driver.update(0.4, 0.98, 200).open).toBe(false);
    // 次のモーラの窓に入ればまた開く
    expect(driver.update(0.4, 1.0, 300).open).toBe(true);
  });

  it("母音モードはタイムラインの母音を返す", () => {
    const timeline = moraTimeline("あいう", 3);
    const driver = new LipSyncDriver(options, timeline);
    expect(driver.update(0.4, 0.2, 0).shape).toBe("a");
    expect(driver.update(0.4, 1.5, 200).shape).toBe("i");
    expect(driver.update(0.4, 2.5, 400).shape).toBe("u");
  });

  it("無音になると閉じて n に戻る", () => {
    const driver = new LipSyncDriver(options, moraTimeline("あ", 1));
    driver.update(0.4, 0.2, 0);
    const closed = driver.update(0, 0.2, 500);
    expect(closed).toEqual({ shape: "n", open: false });
  });

  it("タイムラインが無くても開閉だけは動く", () => {
    const driver = new LipSyncDriver(options, []);
    const frame = driver.update(0.4, 0.2, 0);
    expect(frame.open).toBe(true);
    expect(frame.shape).toBe("a");
  });
});

describe("BlinkScheduler", () => {
  it("指定間隔と長さで瞬きする", () => {
    const scheduler = new BlinkScheduler(1000, 1000, 100, () => 0);
    expect(scheduler.update(500)).toBe(false);
    expect(scheduler.update(1000)).toBe(true);
    expect(scheduler.update(1090)).toBe(true);
    expect(scheduler.update(1200)).toBe(false);
  });

  it("なし設定では瞬きしない", () => {
    const scheduler = new BlinkScheduler(0, 0, 0, () => 0);
    expect(scheduler.update(10_000)).toBe(false);
  });
});

describe("resolveLipSyncOptions", () => {
  it("速度プリセットを数値へ展開する", () => {
    const resolved = resolveLipSyncOptions({
      mode: "vowel",
      speed: "max",
      blink: "often",
    });
    expect(resolved.pollMs).toBe(LIP_SYNC_SPEED_PRESETS.max.pollMs);
    expect(resolved.releaseMs).toBe(LIP_SYNC_SPEED_PRESETS.max.releaseMs);
    expect(resolved.blink.durationMs).toBeGreaterThan(0);
    expect(resolved.openThreshold).toBeGreaterThan(resolved.closeThreshold);
  });
});

describe("speechSpans", () => {
  it("短い隙間は連結し、長い無音は分ける", () => {
    const timeline = [
      { mora: "あ", vowel: "a" as const, start: 0, end: 0.2 },
      { mora: "い", vowel: "i" as const, start: 0.25, end: 0.45 },
      { mora: "、", vowel: "n" as const, start: 1.0, end: 1.2 },
    ];
    const spans = speechSpans(timeline, 0.08);
    expect(spans).toHaveLength(2);
    expect(spans[0]).toEqual({ start: 0, end: 0.45 });
    expect(spans[1]).toEqual({ start: 1.0, end: 1.2 });
    expect(inSpans(spans, 0.1)).toBe(true);
    expect(inSpans(spans, 0.5)).toBe(false);
    expect(inSpans(spans, 1.1)).toBe(true);
  });

  it("空のタイムラインでは区間を作らない", () => {
    expect(speechSpans([])).toEqual([]);
    expect(inSpans([], 1)).toBe(false);
  });
});

describe("moraTimelineFromAnchors", () => {
  it("ASRの文字時刻をモーラへ変換し、拗音・長音を畳む", () => {
    const anchors = [
      { char: "き", start: 0.0, end: 0.16 },
      { char: "ゃ", start: 0.16, end: 0.24 },
      { char: "ー", start: 0.24, end: 0.4 },
      { char: "り", start: 0.4, end: 0.56 },
      { char: "ん", start: 0.56, end: 0.72 },
    ];
    const steps = moraTimelineFromAnchors(anchors);
    expect(steps).toHaveLength(3);
    expect(steps[0]).toEqual({ mora: "き", vowel: "a", start: 0, end: 0.4 });
    expect(steps[1].vowel).toBe("i");
    expect(steps[2]).toEqual({
      mora: "ん",
      vowel: "n",
      start: 0.56,
      end: 0.72,
    });
  });

  it("句読点が混じっても母音は文字から決まる", () => {
    const steps = moraTimelineFromAnchors([
      { char: "あ", start: 0.1, end: 0.3 },
      { char: "、", start: 0.3, end: 0.5 },
      { char: "え", start: 0.5, end: 0.7 },
    ]);
    expect(steps.map((step) => step.vowel)).toEqual(["a", "n", "e"]);
  });
});

describe("LipSyncDriver (タイムライン基準)", () => {
  const options = resolveLipSyncOptions({
    mode: "simple",
    speed: "fast",
    blink: "normal",
    timelineSource: "mora",
  });

  it("簡易モードでもタイムラインの発話区間でだけ口を開く", () => {
    const timeline = moraTimeline("あいうえお", 1.0);
    const driver = new LipSyncDriver(options, timeline);
    // 開いた瞬間はゲートのヒステリシスで開かない（level がしきい値未満）
    expect(driver.update(0, 0.1, 0).open).toBe(false);
    expect(driver.update(0.5, 0.11, 20)).toEqual({ shape: "a", open: true });
    // 発話区間の外（末尾の余白）では閉じる
    const tail = timeline[timeline.length - 1].end + 0.5;
    for (let time = 40; time < 400; time += 20) driver.update(0.5, 1.0, time);
    expect(driver.update(0.5, tail, 420).open).toBe(false);
  });

  it("タイムラインが無いときは音量だけで開閉する（従来動作）", () => {
    const driver = new LipSyncDriver(options, []);
    expect(driver.update(0.5, 0.1, 0).open).toBe(true);
    expect(driver.update(0, 0.2, 30).open).toBe(true); // release中は開いたまま
    expect(driver.update(0, 0.3, 5000).open).toBe(false);
  });
});

describe("flapWindows", () => {
  it("モーラごとに開閉の窓を作り、終わりに閉じる時間を残す", () => {
    const timeline = [
      { mora: "あ", vowel: "a" as const, start: 0, end: 0.2 },
      { mora: "い", vowel: "i" as const, start: 0.2, end: 0.4 },
      { mora: "う", vowel: "u" as const, start: 0.4, end: 0.45 },
    ];
    const windows = flapWindows(timeline, 0.06, 0.06);
    expect(windows).toHaveLength(3);
    expect(windows[0]).toEqual({ start: 0, end: 0.14 });
    // 最後のモーラは短いので、モーラ長ぶんだけ開く（窓はモーラからはみ出さない）
    expect(windows[2].end - windows[2].start).toBeCloseTo(0.05, 5);
    expect(inSpans(windows, 0.17)).toBe(false); // 窓の間は閉じている
  });
});

describe("LipSyncDriver 簡易モードのリズム", () => {
  it("モーラごとに開閉し、口の開閉回数がモーラ数と一致する", () => {
    const timeline = moraTimeline("あいうえお", 1.0);
    const options = resolveLipSyncOptions({
      mode: "simple",
      speed: "normal",
      blink: "off",
      timelineSource: "mora",
    });
    const driver = new LipSyncDriver(options, timeline);
    let transitions = 0;
    let previous = false;
    const stepMs = 10;
    for (let ms = 0; ms <= 2000; ms += stepMs) {
      const seconds = ms / 1000;
      const frame = driver.update(0.4, seconds, ms);
      if (frame.open !== previous) transitions++;
      previous = frame.open;
    }
    // 5モーラ → 開いて閉じるで 約10回（両端のぶん多少ずれる）
    expect(transitions).toBeGreaterThanOrEqual(8);
    expect(transitions).toBeLessThanOrEqual(12);
  });
});

describe("ASRの認識漏れと再生時刻", () => {
  it.each(["simple", "vowel"] as const)(
    "%s: 認識漏れは音量で補い、無音では閉じる",
    (mode) => {
      const driver = new LipSyncDriver(
        resolveLipSyncOptions({
          mode,
          speed: "fast",
          blink: "off",
          timelineSource: "asr",
        }),
        [
          { mora: "あ", vowel: "a", start: 0, end: 0.3 },
          { mora: "い", vowel: "i", start: 1, end: 1.3 },
        ],
      );
      expect(driver.update(0.4, 0.5, 0).open).toBe(true);
      expect(driver.update(0, 0.6, 500).open).toBe(false);
      expect(driver.update(0.4, 1.5, 1000).open).toBe(true);
    },
  );
  it("120ms先読みせず短い発話も実際の時刻で開く", () => {
    const driver = new LipSyncDriver(
      resolveLipSyncOptions({ mode: "simple", speed: "fast", blink: "off" }),
      [{ mora: "あ", vowel: "a", start: 0.5, end: 0.6 }],
    );
    expect(driver.update(0.4, 0.4, 0).open).toBe(false);
    expect(driver.update(0.4, 0.51, 110).open).toBe(true);
  });
});
