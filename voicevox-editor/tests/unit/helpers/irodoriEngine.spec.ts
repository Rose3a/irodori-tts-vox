/**
 * Irodori エンジンとのやり取り（トークンの保持・再取得・失敗の扱い）の確認。
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchAsrTimeline,
  fetchIrodoriStatus,
  forgetIrodoriSession,
  irodoriRequest,
} from "@/helpers/irodoriEngine";

const ENDPOINT = "http://127.0.0.1:50125";

type RecordedCall = {
  url: string;
  token: string | undefined;
  method: string;
  contentType: string | undefined;
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function mockFetch(
  handler: (url: string, init: RequestInit) => Response | Promise<Response>,
): RecordedCall[] {
  const calls: RecordedCall[] = [];
  vi.stubGlobal(
    "fetch",
    async (input: RequestInfo | URL, init: RequestInit = {}) => {
      const url = String(input);
      const headers = new Headers(init.headers);
      calls.push({
        url,
        token: headers.get("X-Irodori-Session") ?? undefined,
        method: init.method ?? "GET",
        contentType: headers.get("Content-Type") ?? undefined,
      });
      return await handler(url, init);
    },
  );
  return calls;
}

const isSession = (url: string) => url.endsWith("/irodori/session");

beforeEach(() => {
  forgetIrodoriSession();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("irodoriRequest", () => {
  it("トークンは一度だけ取り、以降は使い回す", async () => {
    const calls = mockFetch((url) =>
      isSession(url) ? jsonResponse({ token: "t1" }) : jsonResponse({ ok: true }),
    );

    await irodoriRequest(ENDPOINT, "/irodori/settings");
    await irodoriRequest(ENDPOINT, "/irodori/settings");

    expect(calls.filter((call) => isSession(call.url)).length).toBe(1);
    const apiCalls = calls.filter((call) => !isSession(call.url));
    expect(apiCalls.map((call) => call.token)).toStrictEqual(["t1", "t1"]);
  });

  it("403 ならトークンを取り直して一度だけやり直す", async () => {
    let sessionCount = 0;
    const calls = mockFetch((url, init) => {
      if (isSession(url)) {
        sessionCount += 1;
        return jsonResponse({ token: `t${sessionCount}` });
      }
      const token = new Headers(init.headers).get("X-Irodori-Session");
      return token === "t2"
        ? jsonResponse({ ok: true })
        : jsonResponse({ detail: "invalid local origin/session" }, 403);
    });

    const response = await irodoriRequest(ENDPOINT, "/irodori/settings");

    expect(response.status).toBe(200);
    expect(sessionCount).toBe(2);
    const apiCalls = calls.filter((call) => !isSession(call.url));
    expect(apiCalls.map((call) => call.token)).toStrictEqual(["t1", "t2"]);
  });

  it("POST は本文を JSON で送る", async () => {
    const calls = mockFetch((url) =>
      isSession(url)
        ? jsonResponse({ token: "t1" })
        : jsonResponse({ ok: true }),
    );

    await irodoriRequest(ENDPOINT, "/irodori/settings", {
      method: "POST",
      body: { backend: "radeon" },
    });

    const apiCall = calls.find((call) => !isSession(call.url));
    expect(apiCall?.method).toBe("POST");
    expect(apiCall?.contentType).toBe("application/json");
  });

  it("セッション取得に失敗した約束を握り続けない", async () => {
    let failing = true;
    mockFetch((url) => {
      if (isSession(url) && failing) throw new Error("engine is down");
      return isSession(url)
        ? jsonResponse({ token: "t1" })
        : jsonResponse({ ok: true });
    });

    await expect(
      irodoriRequest(ENDPOINT, "/irodori/settings"),
    ).rejects.toThrow("engine is down");

    failing = false;
    const response = await irodoriRequest(ENDPOINT, "/irodori/settings");
    expect(response.status).toBe(200);
  });
});

describe("fetchIrodoriStatus", () => {
  it("失敗は本文つきの例外にする", async () => {
    mockFetch((url) =>
      isSession(url)
        ? jsonResponse({ token: "t1" })
        : new Response("設定を読めません", { status: 409 }),
    );

    await expect(fetchIrodoriStatus(ENDPOINT)).rejects.toThrow(
      /設定の通信に失敗しました \(409\): 設定を読めません/,
    );
  });
});

describe("fetchAsrTimeline", () => {
  const audio = () => new Blob([new Uint8Array([1, 2, 3])]);

  it("available が false なら null（口パクを付けるだけなので）", async () => {
    mockFetch((url) =>
      isSession(url)
        ? jsonResponse({ token: "t1" })
        : jsonResponse({ available: false, reason: "ASR model is downloading" }),
    );

    await expect(
      fetchAsrTimeline(ENDPOINT, "こんにちは", audio()),
    ).resolves.toBeNull();
  });

  it("anchors があればそのまま返す", async () => {
    const anchors = [{ char: "こ", start: 0.1, end: 0.3 }];
    mockFetch((url) =>
      isSession(url)
        ? jsonResponse({ token: "t1" })
        : jsonResponse({ available: true, anchors, audioSeconds: 1.2 }),
    );

    const result = await fetchAsrTimeline(ENDPOINT, "こんにちは", audio());

    expect(result?.anchors).toStrictEqual(anchors);
  });
});
