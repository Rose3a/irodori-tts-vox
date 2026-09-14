"""エンジンを再起動してもエディタが繋がり続けるか（トークンの取り直し）の確認。

やること:
  1. 予備ポートでエンジンを起動し、ヘッドレスChromeでエディタを開く
  2. ページ内の本物のクライアント（helpers/irodoriEngine.ts と
     infrastructures/EngineConnector.ts）でトークンを取得してAPIを叩く
  3. エンジンを再起動する（セッショントークンは起動ごとに変わる）
  4. 古いトークンが 403 になることと、クライアントが取り直して成功することを見る

確認に使う口はトークンを見るものに限る。GET /speakers と /version は _authorized() を
通らないので、古いトークンでも 200 が返り「取り直した」ことの証拠にならない。
EngineConnector 側は POST /audio_query（do_POST が認証必須）で確かめる。

結果は logs\\verify-token-recovery.json に残す。
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

import websockets

# Chrome の場所は IRODORI_CHROME で差し替えられる（既定は Windows の標準インストール先）。
CHROME = os.environ.get(
    "IRODORI_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
BOX = Path(__file__).resolve().parents[1]
APP = "http://127.0.0.1:5173/"
PORT = 9334
ENGINE_PORT = 50199
ENGINE = f"http://127.0.0.1:{ENGINE_PORT}"
PROFILE = Path(tempfile.gettempdir()) / "chrome-cdp-token-recovery"
OUT = BOX / "logs"


def engine_up() -> bool:
    try:
        with urllib.request.urlopen(ENGINE + "/version", timeout=3) as response:
            return response.status == 200
    except Exception:
        return False


def start_engine() -> subprocess.Popen:
    log = (OUT / "token-recovery-engine.log").open("ab")
    proc = subprocess.Popen(
        [sys.executable, "-u", str(BOX / "irodori-tts" / "wrapper" / "editor_engine.py"),
         "--host", "127.0.0.1", "--port", str(ENGINE_PORT)],
        cwd=str(BOX), stdout=log, stderr=log)
    for _ in range(120):
        if engine_up():
            return proc
        time.sleep(1)
    proc.kill()
    raise SystemExit("engine did not start")


def stop_engine(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
    for _ in range(60):
        if not engine_up():
            return
        time.sleep(1)
    raise SystemExit("engine did not stop")


BEFORE_RESTART = f"""
(async () => {{
  const out = {{}};
  const helper = await import("/helpers/irodoriEngine.ts");
  const connector = await import("/infrastructures/EngineConnector.ts");
  const api = connector.OpenAPIEngineConnectorFactory.instance("{ENGINE}");
  try {{
    const status = await helper.fetchIrodoriStatus("{ENGINE}");
    out.helperBefore = status?.settings?.backend ?? null;
    out.tokenBefore = await helper.irodoriSessionToken("{ENGINE}");
    window.__irodoriHelper = helper;
    window.__irodoriApi = api;
    window.__irodoriTokenBefore = out.tokenBefore;
    // トークンが要る口で叩く。GET /speakers は認証を通らないので使えない。
    out.queryBefore = (await api.audioQuery({{ text: "こんにちは", speaker: 0 }})) != null;
  }} catch (error) {{
    out.error = String(error);
  }}
  return out;
}})()
"""

AFTER_RESTART = f"""
(async () => {{
  const out = {{}};
  const helper = window.__irodoriHelper;
  try {{
    const stale = await fetch("{ENGINE}/irodori/settings",
      {{ headers: {{ "X-Irodori-Session": window.__irodoriTokenBefore }} }});
    out.staleTokenStatus = stale.status;
  }} catch (error) {{
    out.staleError = String(error);
  }}
  try {{
    const status = await helper.fetchIrodoriStatus("{ENGINE}");
    out.helperAfter = status?.settings?.backend ?? null;
    out.tokenAfter = await helper.irodoriSessionToken("{ENGINE}");
  }} catch (error) {{
    out.helperError = String(error);
  }}
  try {{
    // 再起動でトークンが変わっているので、ここは一度 403 になって取り直す経路。
    out.queryAfter = (await window.__irodoriApi.audioQuery({{ text: "こんにちは", speaker: 0 }})) != null;
  }} catch (error) {{
    out.connectorError = String(error);
  }}
  return out;
}})()
"""


async def main() -> int:
    OUT.mkdir(exist_ok=True)
    report: dict = {"ok": False}

    chrome = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", "--disable-extensions",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
        "--window-size=1400,900", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    engine = start_engine()
    try:
        for _ in range(60):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=5)
                break
            except Exception:
                time.sleep(0.5)
        listing = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{PORT}/json/list", timeout=10).read())
        ws_url = [t for t in listing if t["type"] == "page"][0]["webSocketDebuggerUrl"]

        async with websockets.connect(ws_url, max_size=64 * 1024 * 1024) as ws:
            counter = 0

            async def send(method, params=None):
                nonlocal counter
                counter += 1
                await ws.send(json.dumps({"id": counter, "method": method, "params": params or {}}))
                while True:
                    message = json.loads(await ws.recv())
                    if message.get("id") == counter:
                        return message

            async def evaluate(expression):
                result = await send("Runtime.evaluate", {
                    "expression": expression, "returnByValue": True, "awaitPromise": True})
                value = result.get("result", {}).get("result", {})
                if "value" in value:
                    return value["value"]
                return {"error": value.get("description")}

            await send("Page.enable")
            await send("Runtime.enable")
            await send("Page.navigate", {"url": APP})
            for _ in range(90):
                await asyncio.sleep(1)
                state = await evaluate("!!document.querySelector('#app')?.children.length")
                if state is True:
                    break
            report["mounted"] = state is True
            # アプリの起動処理が落ち着くまで少し待つ
            await asyncio.sleep(5)

            report["before"] = await evaluate(BEFORE_RESTART)

            stop_engine(engine)
            engine = start_engine()
            report["engine_restarted"] = True

            after = await evaluate(AFTER_RESTART)
            report["after"] = after
            report["token_changed"] = (
                report["before"].get("tokenBefore") != after.get("tokenAfter"))
            report["ok"] = bool(
                report["mounted"]
                and report["before"].get("helperBefore")
                and report["before"].get("queryBefore") is True
                and after.get("staleTokenStatus") == 403
                and after.get("helperAfter")
                and after.get("queryAfter") is True
                and report["token_changed"]
                and not report["before"].get("error")
                and not after.get("helperError")
                and not after.get("connectorError")
            )
    finally:
        chrome.terminate()
        stop_engine(engine)
        (OUT / "verify-token-recovery.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
