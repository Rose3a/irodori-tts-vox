/**
 * Irodori エンジン（ローカルの FastAPI/HTTP サーバ）との通信をまとめる。
 *
 * エンジンは起動ごとに作られるセッショントークンを要求するので、
 * ここで一度取得して使い回す。
 */

export type AsrAnchor = {
  char: string;
  start: number;
  end: number;
};

export type AsrTimelineResponse = {
  available: boolean;
  text?: string;
  asrText?: string;
  anchors?: AsrAnchor[];
  resolution?: number;
  audioSeconds?: number;
  asrSeconds?: number;
  reason?: string;
  modelFolder?: string;
};

const sessionTokens = new Map<string, string>();

async function authHeaders(
  endpoint: string,
  json = false,
): Promise<Record<string, string>> {
  let token = sessionTokens.get(endpoint);
  if (token == undefined) {
    const response = await fetch(`${endpoint}/irodori/session`, {
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("engine session unavailable");
    token = ((await response.json()) as { token: string }).token;
    sessionTokens.set(endpoint, token);
  }
  return {
    ...(json ? { "Content-Type": "application/json" } : {}),
    "X-Irodori-Session": token,
  };
}

export function forgetIrodoriSession(endpoint?: string): void {
  if (endpoint == undefined) sessionTokens.clear();
  else sessionTokens.delete(endpoint);
}

/**
 * セリフの文字ごとの発話時刻をエンジンから取る。
 *
 * 再生対象の音声そのものを送信し、別の生成結果との取り違えを防ぐ。
 */
export async function fetchAsrTimeline(
  endpoint: string,
  text: string,
  audio: Blob,
  timeoutMs = 60000,
): Promise<AsrTimelineResponse | null> {
  try {
    const wav = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string")
          resolve(reader.result.split(",")[1]);
        else reject(new Error("音声を読み込めませんでした"));
      };
      reader.onerror = () =>
        reject(reader.error ?? new Error("音声を読み込めませんでした"));
      reader.readAsDataURL(audio);
    });
    const headers = await authHeaders(endpoint, true);
    const response = await fetch(`${endpoint}/irodori/timeline`, {
      method: "POST",
      headers,
      body: JSON.stringify({ text, wav }),
      signal: AbortSignal.timeout(timeoutMs),
    });
    if (response.status === 403) {
      // トークンがエンジンの再起動で変わった
      forgetIrodoriSession(endpoint);
      return null;
    }
    if (!response.ok) return null;
    const result = (await response.json()) as AsrTimelineResponse;
    if (!result.available || !result.anchors || result.anchors.length === 0)
      return null;
    return result;
  } catch {
    return null;
  }
}

/** 行設定の既定値を、現在選ばれているモデルに合わせる。 */
export async function fetchIrodoriDefaultSteps(
  endpoint: string,
): Promise<number | undefined> {
  try {
    const response = await fetch(`${endpoint}/irodori/settings`, {
      headers: await authHeaders(endpoint),
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) return undefined;
    const result = (await response.json()) as {
      modelInfo?: { defaultSteps?: number };
    };
    return result.modelInfo?.defaultSteps;
  } catch {
    return undefined;
  }
}
