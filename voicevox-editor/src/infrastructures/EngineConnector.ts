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
  const sessionToken = (host: string): Promise<string> => {
    tokenPromises[host] ??= fetch(`${host}/irodori/session`)
      .then((response) => {
        if (!response.ok) throw new Error(`engine session unavailable (${response.status})`);
        return response.json() as Promise<{ token: string }>;
      })
      .then(({ token }) => token);
    return tokenPromises[host];
  };
  return {
    instance: (host: string) => {
      const cached = instanceMapper[host];
      if (cached != undefined) {
        return cached;
      }
      const api = new DefaultApi(new Configuration({
        basePath: host,
        fetchApi: async (input, init = {}) => {
          const url = typeof input === "string" ? input : input.toString();
          const headers = new Headers(init.headers);
          if (!url.endsWith("/irodori/session")) {
            headers.set("X-Irodori-Session", await sessionToken(host));
          }
          return fetch(input, { ...init, headers });
        },
      }));
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
