/**
 * エンジンとの接続（VOICEVOX 互換API）でトークンがどう扱われるかの確認。
 *
 * エンジンは起動ごとにセッショントークンを作り直すので、
 * エディタを開いたまま再起動しても会話が続く必要がある。
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { OpenAPIEngineConnectorFactory } from "@/infrastructures/EngineConnector";

/**
 * このモジュールは接続先ごとにトークンとAPIインスタンスを保持し続けるので、
 * テストごとに別のポートを使い、状態が混ざらないようにする。
 */
const hostFor = (port: number) => `http://127.0.0.1:${port}`;

type RecordedCall = {
  url: string;
  token: string | undefined;
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
      });
      return await handler(url, init);
    },
  );
  return calls;
}

const isSession = (url: string) => url.endsWith("/irodori/session");

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("OpenAPIEngineConnectorFactory", () => {
  it("取得したトークンを付けてAPIを呼ぶ", async () => {
    const host = hostFor(50201);
    const calls = mockFetch((url) =>
      isSession(url) ? jsonResponse({ token: "t1" }) : jsonResponse(["1.0.0"]),
    );

    const api = OpenAPIEngineConnectorFactory.instance(host);
    await api.coreVersions();
    await api.coreVersions();

    expect(calls.filter((call) => isSession(call.url)).length).toBe(1);
    const apiCalls = calls.filter((call) => !isSession(call.url));
    expect(apiCalls.map((call) => call.token)).toStrictEqual(["t1", "t1"]);
  });

  it("403 ならトークンを取り直して一度だけやり直す", async () => {
    const host = hostFor(50202);
    let sessionCount = 0;
    const calls = mockFetch((url, init) => {
      if (isSession(url)) {
        sessionCount += 1;
        return jsonResponse({ token: `t${sessionCount}` });
      }
      const token = new Headers(init.headers).get("X-Irodori-Session");
      return token === "t2"
        ? jsonResponse(["1.0.0"])
        : new Response("forbidden", { status: 403 });
    });

    const api = OpenAPIEngineConnectorFactory.instance(host);
    await expect(api.coreVersions()).resolves.toStrictEqual(["1.0.0"]);

    expect(sessionCount).toBe(2);
    const apiCalls = calls.filter((call) => !isSession(call.url));
    expect(apiCalls.map((call) => call.token)).toStrictEqual(["t1", "t2"]);
  });

  it("起動前に失敗したセッション取得を握り続けない", async () => {
    const host = hostFor(50203);
    let engineUp = false;
    mockFetch((url) => {
      if (isSession(url)) {
        if (!engineUp) throw new Error("connection refused");
        return jsonResponse({ token: "t1" });
      }
      return jsonResponse(["1.0.0"]);
    });

    const api = OpenAPIEngineConnectorFactory.instance(host);
    await expect(api.coreVersions()).rejects.toThrow();

    engineUp = true;
    await expect(api.coreVersions()).resolves.toStrictEqual(["1.0.0"]);
  });
});
