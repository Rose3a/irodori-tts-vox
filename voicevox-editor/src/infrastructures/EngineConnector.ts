import { createEngineUrl, type EngineUrlParams } from "@/domain/url";
import { createOpenAPIEngineMock } from "@/mock/engineMock";
import { Configuration, DefaultApi, type DefaultApiInterface } from "@/openapi";

export interface IEngineConnectorFactory {
  // FIXME: hostという名前の時点で外部APIに接続するという知識が出てきてしまっているので
  // Factory自体に型パラメータを付けて、接続方法だったり設定、IDみたいな名前で表現する
  instance: (host: string) => DefaultApiInterface;
}

// 通常エンジン
const OpenAPIEngineConnectorFactoryImpl = (): IEngineConnectorFactory => {
  const instanceMapper: Record<string, DefaultApiInterface> = {};
  const tokenPromises: Record<string, Promise<string>> = {};
  // 起動直後は失敗するので、失敗した約束は握り続けず捨てる。
  // エンジンの再起動でトークンが変わったときは force で取り直す。
  const sessionToken = (host: string, force = false): Promise<string> => {
    if (force) delete tokenPromises[host];
    tokenPromises[host] ??= fetch(`${host}/irodori/session`)
      .then((response) => {
        if (!response.ok)
          throw new Error(`engine session unavailable (${response.status})`);
        return response.json() as Promise<{ token: string }>;
      })
      .then(({ token }) => token)
      .catch((cause: unknown) => {
        delete tokenPromises[host];
        throw cause;
      });
    return tokenPromises[host];
  };
  return {
    instance: (host: string) => {
      const cached = instanceMapper[host];
      if (cached != undefined) {
        return cached;
      }
      const api = new DefaultApi(
        new Configuration({
          basePath: host,
          fetchApi: async (input, init = {}) => {
            const url =
              typeof input === "string"
                ? input
                : input instanceof URL
                  ? input.href
                  : input.url;
            const send = async (token: string) => {
              const headers = new Headers(init.headers);
              headers.set("X-Irodori-Session", token);
              return await fetch(input, { ...init, headers });
            };
            if (url.endsWith("/irodori/session")) {
              return await fetch(input, init);
            }
            const response = await send(await sessionToken(host));
            if (response.status !== 403) return response;
            // エンジンが再起動するとトークンが変わる。取り直して一度だけやり直す。
            return await send(await sessionToken(host, true));
          },
        }),
      );
      instanceMapper[host] = api;

      return api;
    },
  };
};
export const OpenAPIEngineConnectorFactory =
  OpenAPIEngineConnectorFactoryImpl();

// モック用エンジン
const OpenAPIMockEngineConnectorFactoryImpl = (): IEngineConnectorFactory => {
  let mockInstance: DefaultApiInterface | undefined;
  return {
    instance: () => {
      if (!mockInstance) {
        mockInstance = createOpenAPIEngineMock();
      }
      return mockInstance;
    },
  };
};
export const OpenAPIMockEngineConnectorFactory =
  OpenAPIMockEngineConnectorFactoryImpl();

// 通常エンジンとモック用エンジンの両対応
// モック用エンジンのURLのときはモックを、そうじゃないときは通常エンジンを返す。
const OpenAPIEngineAndMockConnectorFactoryImpl =
  (): IEngineConnectorFactory => {
    // モック用エンジンのURLは `mock://mock` とする
    const mockUrlParams: EngineUrlParams = {
      protocol: "mock:",
      hostname: "mock",
      port: "",
      pathname: "",
    };

    return {
      instance: (host: string) => {
        if (host == createEngineUrl(mockUrlParams)) {
          return OpenAPIMockEngineConnectorFactory.instance(host);
        } else {
          return OpenAPIEngineConnectorFactory.instance(host);
        }
      },
    };
  };
export const OpenAPIEngineAndMockConnectorFactory =
  OpenAPIEngineAndMockConnectorFactoryImpl();
