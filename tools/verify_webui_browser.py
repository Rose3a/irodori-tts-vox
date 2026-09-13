"""ヘッドレスChromeをCDPで操作して WebUI を実レンダリング確認する。

やること:
  1. 127.0.0.1:5173 の Irodori VOICEVOX Editor を開く
  2. Vue アプリがマウントするまで待つ
  3. 画面テキスト・コンソールエラー・失敗リクエストを集める
  4. ページ内からエンジン(50125)へ fetch して、ブラウザ文脈で CORS+セッションが通るか確認
  5. スクリーンショットを保存
"""
from __future__ import annotations

import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import websockets

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
APP = "http://127.0.0.1:5173/"
ENGINE = "http://127.0.0.1:50125"
PORT = 9333
PROFILE = Path(tempfile.gettempdir()) / "chrome-cdp-verify"
OUT = Path(__file__).resolve().parents[1] / "logs"


def http_json(url: str):
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.loads(response.read())


async def main() -> int:
    proc = subprocess.Popen([
        CHROME, "--headless=new", "--disable-gpu", "--no-first-run",
        "--no-default-browser-check", "--disable-extensions",
        f"--remote-debugging-port={PORT}", f"--user-data-dir={PROFILE}",
        "--window-size=1600,1000", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    report: dict = {"console": [], "failed_requests": [], "ok": False}
    try:
        for _ in range(60):
            try:
                http_json(f"http://127.0.0.1:{PORT}/json/version")
                break
            except Exception:
                time.sleep(0.5)
        else:
            raise SystemExit("chrome devtools endpoint did not start")

        pages = [t for t in http_json(f"http://127.0.0.1:{PORT}/json/list") if t["type"] == "page"]
        ws_url = pages[0]["webSocketDebuggerUrl"]

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
                    if message.get("method") == "Runtime.consoleAPICalled":
                        report["console"].append(" ".join(
                            str(a.get("value")) for a in message["params"].get("args", [])))
                    elif message.get("method") == "Log.entryAdded":
                        entry = message["params"]["entry"]
                        report["console"].append(f"{entry.get('level')}: {entry.get('text')}")
                    elif message.get("method") == "Network.loadingFailed":
                        report["failed_requests"].append(message["params"].get("errorText"))

            async def evaluate(expression):
                result = await send("Runtime.evaluate", {
                    "expression": expression, "returnByValue": True, "awaitPromise": True})
                return result.get("result", {}).get("result", {}).get("value")

            for domain in ("Page", "Runtime", "Log", "Network"):
                await send(f"{domain}.enable")
            await send("Page.navigate", {"url": APP})

            mounted = False
            for _ in range(90):
                await asyncio.sleep(1)
                try:
                    state = await evaluate(
                        "(() => ({title: document.title,"
                        " text: document.body.innerText,"
                        " app: !!document.querySelector('#app'),"
                        " children: document.querySelector('#app')?.children.length ?? -1}))()")
                except Exception:
                    continue
                if state and state.get("children", 0) > 0:
                    mounted = True
                    report["title"] = state["title"]
                    report["text"] = (state.get("text") or "")[:2000]
                    break
            report["mounted"] = mounted

            # ブラウザ文脈でのエンジン疎通（fetch は Origin が自動で付く）
            report["engine_probe"] = await evaluate(f"""
                (async () => {{
                  const out = {{}};
                  try {{
                    const version = await fetch("{ENGINE}/version");
                    out.version = [version.status, await version.text()];
                    const session = await fetch("{ENGINE}/irodori/session");
                    out.session_status = session.status;
                    const token = (await session.json()).token;
                    const settings = await fetch("{ENGINE}/irodori/settings",
                      {{ headers: {{ "X-Irodori-Session": token }} }});
                    out.settings_status = settings.status;
                    const body = await settings.json();
                    out.backend = body?.settings?.backend;
                    out.model = body?.settings?.model;
                  }} catch (error) {{
                    out.error = String(error);
                  }}
                  return out;
                }})()""")

            shot = await send("Page.captureScreenshot", {"format": "png"})
            data = shot.get("result", {}).get("data")
            if data:
                target = OUT / "webui-verification.png"
                target.write_bytes(base64.b64decode(data))
                report["screenshot"] = str(target)
            report["ok"] = bool(mounted)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
        (OUT / "webui-verification.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k != "console"},
                         ensure_ascii=False, indent=2))
        print("console entries:", len(report["console"]))
        for line in report["console"][:15]:
            print("  ", line)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
