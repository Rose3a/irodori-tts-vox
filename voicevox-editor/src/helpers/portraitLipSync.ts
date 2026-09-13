/**
 * 立ち絵の口パク制御。
 *
 * 2段階の精度を扱う。
 * - simple: 通常/口パクの2枚（全体立ち絵）を開閉で切り替える。切り替え速度は可変。
 * - vowel : あいうえおの口パーツがある場合に、母音ごとに切り替える。
 *
 * 母音の時刻は「タイムライン」で与える。タイムラインは音声の長さとセリフから
 * モーラ数比例で作れるため、ASRや強制アラインメントが無くても動く。
 * 音量（RMSエンベロープ）は口の開き具合に使い、母音は形の選択に使う。
 */

/** 20ms のRMSエンベロープ。音声の追加ルーティングはしない。 */
export const ENVELOPE_SECONDS = 0.02;

export type LipSyncMode = "off" | "simple" | "vowel";

/** 母音タイムラインの作り方。mora=セリフから推定、asr=ASRのトークン時刻から。 */
export type TimelineSource = "mora" | "asr";

export const TIMELINE_SOURCE_LABELS: Record<TimelineSource, string> = {
  mora: "推定（文字数から）",
  asr: "ASR（発話時刻から）",
};

/** n = 口を閉じた状態（無音・鼻音・促音） */
export type MouthShape = "n" | "a" | "i" | "u" | "e" | "o";

export const MOUTH_SHAPES: readonly MouthShape[] = [
  "n",
  "a",
  "i",
  "u",
  "e",
  "o",
];

/** 切り替え速度のプリセット。数値は口パクの判定間隔と閉じるまでの猶予(ms)。 */
export type LipSyncSpeed = "slow" | "normal" | "fast" | "max";

export const LIP_SYNC_SPEED_PRESETS: Record<
  LipSyncSpeed,
  {
    pollMs: number;
    releaseMs: number;
    vowelHoldMs: number;
    /** 簡易立ち絵で、モーラとモーラの間で口を閉じている時間。 */
    flapGapMs: number;
    label: string;
  }
> = {
  slow: {
    pollMs: 100,
    releaseMs: 220,
    vowelHoldMs: 140,
    flapGapMs: 100,
    label: "ゆっくり",
  },
  normal: {
    pollMs: 40,
    releaseMs: 80,
    vowelHoldMs: 90,
    flapGapMs: 65,
    label: "標準",
  },
  fast: {
    pollMs: 24,
    releaseMs: 50,
    vowelHoldMs: 60,
    flapGapMs: 40,
    label: "速い",
  },
  max: {
    pollMs: 16,
    releaseMs: 30,
    vowelHoldMs: 45,
    flapGapMs: 25,
    label: "最速",
  },
};

export type LipSyncBlink = "off" | "normal" | "often";

export const LIP_SYNC_BLINK_PRESETS: Record<
  LipSyncBlink,
  { minMs: number; maxMs: number; durationMs: number; label: string }
> = {
  off: { minMs: 0, maxMs: 0, durationMs: 0, label: "なし" },
  normal: { minMs: 2200, maxMs: 5400, durationMs: 160, label: "標準" },
  often: { minMs: 1200, maxMs: 2800, durationMs: 110, label: "多め" },
};

export type LipSyncOptions = {
  mode: LipSyncMode;
  speed: LipSyncSpeed;
  blink: LipSyncBlink;
  /** タイムラインの作り方（設定で切り替え）。 */
  timelineSource?: TimelineSource;
  /** 口を開き始めるRMS。 */
  openThreshold?: number;
  /** 閉じる側のしきい値（ヒステリシス）。 */
  closeThreshold?: number;
};

export type ResolvedLipSyncOptions = {
  mode: LipSyncMode;
  timelineSource: TimelineSource;
  pollMs: number;
  releaseMs: number;
  vowelHoldMs: number;
  /** 簡易立ち絵でモーラの切れ目に口を閉じる時間(ms)。 */
  flapGapMs: number;
  openThreshold: number;
  closeThreshold: number;
  blink: { minMs: number; maxMs: number; durationMs: number };
};

export function resolveLipSyncOptions(
  options: LipSyncOptions,
): ResolvedLipSyncOptions {
  const speed =
    LIP_SYNC_SPEED_PRESETS[options.speed] ?? LIP_SYNC_SPEED_PRESETS.normal;
  const blink =
    LIP_SYNC_BLINK_PRESETS[options.blink] ?? LIP_SYNC_BLINK_PRESETS.normal;
  return {
    mode: options.mode,
    timelineSource: options.timelineSource ?? "mora",
    pollMs: speed.pollMs,
    releaseMs: speed.releaseMs,
    vowelHoldMs: speed.vowelHoldMs,
    flapGapMs: speed.flapGapMs,
    openThreshold: options.openThreshold ?? 0.015,
    closeThreshold: options.closeThreshold ?? 0.008,
    blink: {
      minMs: blink.minMs,
      maxMs: blink.maxMs,
      durationMs: blink.durationMs,
    },
  };
}

export function createVolumeEnvelope(audio: AudioBuffer): Float32Array {
  const frameSize = Math.max(
    1,
    Math.round(audio.sampleRate * ENVELOPE_SECONDS),
  );
  const levels = new Float32Array(Math.ceil(audio.length / frameSize));
  for (let channel = 0; channel < audio.numberOfChannels; channel++) {
    const samples = audio.getChannelData(channel);
    for (let frame = 0; frame < levels.length; frame++) {
      const start = frame * frameSize;
      const end = Math.min(start + frameSize, samples.length);
      let sum = 0;
      for (let i = start; i < end; i++) sum += samples[i] * samples[i];
      // ステレオは位相干渉を避けるためチャンネルごとに評価して最大を取る
      levels[frame] = Math.max(levels[frame], Math.sqrt(sum / (end - start)));
    }
  }
  return levels;
}

/** しきい値とヒステリシスで「今しゃべっているか」を判定する。 */
export class MouthGate {
  private lastVoiceTime = -Infinity;
  private opened = false;

  constructor(
    private openThreshold = 0.015,
    private closeThreshold = 0.008,
    private releaseMs = 80,
  ) {}

  update(level: number, timeMs: number): boolean {
    const threshold = this.opened ? this.closeThreshold : this.openThreshold;
    if (level >= threshold) this.lastVoiceTime = timeMs;
    this.opened = timeMs - this.lastVoiceTime < this.releaseMs;
    return this.opened;
  }

  get isOpen(): boolean {
    return this.opened;
  }
}

// ---------------------------------------------------------------------------
// かな → 母音
// ---------------------------------------------------------------------------

const VOWEL_ROWS: Record<Exclude<MouthShape, "n">, string> = {
  a: "あかさたなはまやらわがざだばぱぁゃゕゎ",
  i: "いきしちにひみりゐぎじぢびぴぃ",
  u: "うくすつぬふむゆるゔぐずづぶぷぅゅゔ",
  e: "えけせてねへめれゑげぜでべぺぇ",
  o: "おこそとのほもよろをごぞどぼぽぉょ",
};

const KANA_TO_VOWEL = new Map<string, MouthShape>();
for (const [vowel, row] of Object.entries(VOWEL_ROWS) as [
  MouthShape,
  string,
][]) {
  for (const char of row) KANA_TO_VOWEL.set(char, vowel);
}

const SMALL_KANA = new Set([..."ゃゅょぁぃぅぇぉゎゕゖ"]);

/** 全角カタカナをひらがなへ寄せる（母音判定用）。 */
function toHiragana(char: string): string {
  const code = char.codePointAt(0);
  if (code == undefined) return char;
  if (code >= 0x30a1 && code <= 0x30f6)
    return String.fromCodePoint(code - 0x60);
  if (char === "ー") return "ー";
  if (char === "ン") return "ん";
  if (char === "ッ") return "っ";
  return char;
}

/**
 * 1文字の母音を返す。母音を持たない文字（句読点・記号）は undefined。
 * ん と っ は口を閉じる "n" を返す。
 */
export function vowelOf(char: string): MouthShape | undefined {
  const kana = toHiragana(char);
  if (kana === "ん" || kana === "っ") return "n";
  return KANA_TO_VOWEL.get(kana);
}

export type MoraStep = {
  mora: string;
  vowel: MouthShape;
  start: number;
  end: number;
};

/** 母音の時間配分に使う重み。小書きかなは前のモーラへ合成する。 */
const MORA_WEIGHTS: Record<string, number> = {
  っ: 0.5,
  ー: 0.6,
  ん: 0.9,
  "、": 0.8,
  "。": 0.8,
  "，": 0.8,
  "．": 0.8,
  " ": 0.4,
  "　": 0.4,
};

/**
 * セリフと音声長からモーラ単位のタイムラインを作る。
 *
 * ASRやアラインメント無しでも「あいうえお」を切り替えられるようにするための
 * 簡易配分。モーラ数を数えて発話時間を比例配分するだけなので、実際の発話と
 * 数十ミリ秒ずれることはあるが、口パクとしては十分目立たない。
 */
export function moraTimeline(
  text: string,
  durationSeconds: number,
): MoraStep[] {
  const chars = [...text].filter((char) => char.trim() !== "");
  const slots: { mora: string; vowel: MouthShape; weight: number }[] = [];

  for (const char of chars) {
    const kana = toHiragana(char);
    const last = slots[slots.length - 1];
    if (SMALL_KANA.has(kana)) {
      // きゃ のような拗音は前のモーラに畳み、母音は小書きかな側に合わせる
      if (last) {
        last.vowel = KANA_TO_VOWEL.get(kana) ?? last.vowel;
        last.weight += 0.35;
      }
      continue;
    }
    if (kana === "ー" && last) {
      // 長音符は直前の母音を伸ばす
      last.weight += MORA_WEIGHTS["ー"];
      continue;
    }
    const vowel = vowelOf(char);
    if (vowel == undefined) {
      slots.push({ mora: char, vowel: "n", weight: MORA_WEIGHTS[kana] ?? 0.7 });
      continue;
    }
    slots.push({ mora: char, vowel, weight: MORA_WEIGHTS[kana] ?? 1 });
  }

  const totalWeight = slots.reduce((sum, slot) => sum + slot.weight, 0);
  if (slots.length === 0 || totalWeight <= 0 || durationSeconds <= 0) return [];

  const scale = durationSeconds / totalWeight;
  const steps: MoraStep[] = [];
  let cursor = 0;
  for (const slot of slots) {
    const start = cursor;
    cursor += slot.weight * scale;
    steps.push({
      mora: slot.mora,
      vowel: slot.vowel,
      start: Number(start.toFixed(4)),
      end: Number(cursor.toFixed(4)),
    });
  }
  return steps;
}

/**
 * ASR が返した文字ごとの時刻から、モーラ単位のタイムラインを作る。
 *
 * ASR は「いつ発話されたか」だけを提供し、母音は入力セリフ（既知）から取る。
 * 小書きかな・長音符は前のモーラへ畳み、終端は後ろの文字の時刻に合わせる。
 */
export function moraTimelineFromAnchors(
  anchors: readonly { char: string; start: number; end: number }[],
): MoraStep[] {
  const steps: MoraStep[] = [];
  for (const anchor of anchors) {
    const kana = toHiragana(anchor.char);
    const last = steps[steps.length - 1];
    if (SMALL_KANA.has(kana) && last) {
      last.vowel = KANA_TO_VOWEL.get(kana) ?? last.vowel;
      last.end = Math.max(last.end, anchor.end);
      continue;
    }
    if (kana === "ー" && last) {
      last.end = Math.max(last.end, anchor.end);
      continue;
    }
    steps.push({
      mora: anchor.char,
      vowel: vowelOf(anchor.char) ?? "n",
      start: Number(anchor.start.toFixed(4)),
      end: Number(anchor.end.toFixed(4)),
    });
  }
  return steps;
}

/** 指定時刻の母音を返す。範囲外・無音区間は undefined。 */
export function vowelAt(
  timeline: readonly MoraStep[],
  seconds: number,
): MouthShape | undefined {
  if (timeline.length === 0) return undefined;
  if (seconds < timeline[0].start) return undefined;
  const last = timeline[timeline.length - 1];
  if (seconds >= last.end) return undefined;
  // 線形探索で十分（モーラ数は多くても数百）
  for (const step of timeline) {
    if (seconds >= step.start && seconds < step.end) return step.vowel;
  }
  return undefined;
}

export type SpeechSpan = { start: number; end: number };

/**
 * モーラの並びから「声が出ている区間」を作る。
 *
 * 短い隙間（促音・無音の切れ目）は連結するので、口パクは飛び飛びにならない。
 * これがタイムライン基準の開閉スケジュールになる。
 */
export function speechSpans(
  timeline: readonly MoraStep[],
  gapSeconds = 0.08,
): SpeechSpan[] {
  const spans: SpeechSpan[] = [];
  for (const step of timeline) {
    const last = spans[spans.length - 1];
    if (last && step.start - last.end <= gapSeconds) {
      last.end = Math.max(last.end, step.end);
      continue;
    }
    spans.push({ start: step.start, end: step.end });
  }
  return spans;
}

/**
 * モーラごとの「口を開いている窓」を作る。
 *
 * 簡易立ち絵（通常/口パクの2枚）でもタイムライン基準で開閉させるため、
 * 1モーラ=1回の開閉になるよう、モーラの終わりに少しだけ閉じる時間を作る。
 * 閉じている時間は速度設定（速いほど短い）で変わる。
 */
export function flapWindows(
  timeline: readonly MoraStep[],
  gapSeconds = 0.065,
  minOpenSeconds = 0.06,
): SpeechSpan[] {
  const windows: SpeechSpan[] = [];
  for (const step of timeline) {
    const duration = Math.max(0, step.end - step.start);
    const open = Math.max(
      Math.min(minOpenSeconds, duration),
      duration - gapSeconds,
    );
    const end = step.start + Math.min(duration, open);
    const previous = windows[windows.length - 1];
    if (previous && previous.end >= end) continue; // 短いモーラは前の窓へ吸収
    windows.push({ start: step.start, end });
  }
  return windows;
}

/** 指定時刻が発話区間の中かどうか。 */
export function inSpans(
  spans: readonly SpeechSpan[],
  seconds: number,
): boolean {
  for (const span of spans) {
    if (seconds >= span.start && seconds < span.end) return true;
  }
  return false;
}

// ---------------------------------------------------------------------------
// ドライバ
// ---------------------------------------------------------------------------

export type LipSyncFrame = {
  shape: MouthShape;
  open: boolean;
};

/**
 * 音量とタイムラインから、その瞬間に表示すべき口の形を決める。
 * 表示側はこの結果を画像の選択に使う。
 */
export class LipSyncDriver {
  private gate: MouthGate;
  private options: ResolvedLipSyncOptions;
  private lastVowel: MouthShape = "n";
  private lastVowelAt = -Infinity;
  private spans: SpeechSpan[] = [];
  private windows: SpeechSpan[] = [];

  constructor(
    options: ResolvedLipSyncOptions,
    private timeline: readonly MoraStep[] = [],
  ) {
    this.options = options;
    this.gate = new MouthGate(
      options.openThreshold,
      options.closeThreshold,
      options.releaseMs,
    );
    this.spans = speechSpans(timeline);
    this.windows = flapWindows(timeline, options.flapGapMs / 1000);
  }

  setOptions(options: ResolvedLipSyncOptions): void {
    this.options = options;
    this.gate = new MouthGate(
      options.openThreshold,
      options.closeThreshold,
      options.releaseMs,
    );
    this.windows = flapWindows(this.timeline, options.flapGapMs / 1000);
  }

  setTimeline(timeline: readonly MoraStep[]): void {
    if (this.timeline === timeline) return;
    this.timeline = timeline;
    this.spans = speechSpans(timeline);
    this.windows = flapWindows(timeline, this.options.flapGapMs / 1000);
    this.lastVowel = "n";
    this.lastVowelAt = -Infinity;
  }

  get pollMs(): number {
    return this.options.pollMs;
  }

  /**
   * @param level 現在のRMS
   * @param seconds 音声の再生位置(秒)
   * @param timeMs performance.now() などの単調時刻
   *
   * ASRの認識漏れ区間では音量にフォールバックする。
   * 音量はその中での微調整（無音のフレームで開かない）に使うので、
   * 簡易立ち絵でもモーラのリズムどおりに開閉する。
   */
  update(level: number, seconds: number, timeMs: number): LipSyncFrame {
    if (this.options.mode === "off") return { shape: "n", open: false };
    const position = seconds;
    const outsideAsr =
      this.options.timelineSource === "asr" && !inSpans(this.spans, position);
    const voiced = this.gate.update(level, timeMs);

    if (this.options.mode === "simple") {
      // 簡易立ち絵: モーラごとの窓で開閉する（タイムライン基準）。
      // タイムラインが無いときだけ音量だけで動かす。
      const open =
        this.windows.length === 0 || outsideAsr
          ? voiced
          : inSpans(this.windows, position) &&
            level >= this.options.closeThreshold;
      this.lastVowel = open ? "a" : "n";
      this.lastVowelAt = open ? timeMs : -Infinity;
      return { shape: open ? "a" : "n", open };
    }

    const inSpeech = this.spans.length === 0 || inSpans(this.spans, position);
    if (!voiced || (!inSpeech && !outsideAsr)) {
      this.lastVowel = "n";
      this.lastVowelAt = -Infinity;
      return { shape: "n", open: false };
    }

    const vowel = vowelAt(this.timeline, seconds) ?? "a";
    // 切り替えが細かすぎるとチラつくので、最短保持時間を設ける
    if (
      vowel !== this.lastVowel &&
      timeMs - this.lastVowelAt < this.options.vowelHoldMs
    ) {
      return {
        shape: this.lastVowel === "n" ? "a" : this.lastVowel,
        open: true,
      };
    }
    if (vowel !== this.lastVowel) this.lastVowelAt = timeMs;
    this.lastVowel = vowel;
    return { shape: vowel, open: true };
  }
}

/** 瞬きのタイミングを決める。update() が true を返したら目を閉じる。 */
export class BlinkScheduler {
  private nextAt = Infinity;
  private closeUntil = -Infinity;

  constructor(
    private minMs: number,
    private maxMs: number,
    private durationMs: number,
    private random: () => number = Math.random,
  ) {
    this.schedule(0);
  }

  private schedule(now: number): void {
    if (this.durationMs <= 0 || this.maxMs <= 0) {
      this.nextAt = Infinity;
      return;
    }
    this.nextAt = now + this.minMs + this.random() * (this.maxMs - this.minMs);
  }

  update(timeMs: number): boolean {
    if (timeMs >= this.closeUntil) this.closeUntil = -Infinity;
    if (timeMs >= this.nextAt && this.closeUntil === -Infinity) {
      this.closeUntil = timeMs + this.durationMs;
      this.schedule(this.closeUntil);
    }
    return timeMs < this.closeUntil;
  }
}
