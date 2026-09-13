"""Exercise the packaged engine on a temporary port and optionally synthesize a WAV."""
import argparse
import io
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
import urllib.error

BOX = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--synthesize', action='store_true')
    args = parser.parse_args()
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    exe = BOX / 'voicevox-editor/release/win-unpacked/irodori-engine.exe'
    proc = subprocess.Popen([str(exe), '--port', str(port)], creationflags=subprocess.CREATE_NO_WINDOW)
    report = {'port': port, 'ok': False}
    start = time.monotonic()
    def request(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', data=data, headers={'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=1200) as response:
                body = response.read()
                return json.loads(body) if 'json' in response.headers.get('Content-Type','') else body
        except urllib.error.HTTPError as exc:
            raise RuntimeError(exc.read().decode('utf-8', errors='replace')) from exc
    try:
        for _ in range(120):
            if proc.poll() is not None: raise RuntimeError('Engine exited before becoming ready')
            try:
                report['version'] = request('/version')
                break
            except (urllib.error.URLError, ConnectionError): time.sleep(0.5)
        else: raise TimeoutError('Engine readiness timed out')
        report['startup_seconds'] = round(time.monotonic()-start, 2)
        report['status'] = request('/irodori/settings')
        report['speakers'] = len(request('/speakers'))
        assert 'model.safetensors' in report['status']['models'], report
        if args.synthesize:
            query = request('/audio_query?text=%E3%81%93%E3%82%93%E3%81%AB%E3%81%A1%E3%81%AF&speaker=0', {})
            wav = request('/synthesis?speaker=0', query)
            import soundfile as sf
            import numpy as np
            samples, rate = sf.read(io.BytesIO(wav))
            assert len(samples) > 0 and np.isfinite(samples).all() and np.max(np.abs(samples)) > 0
            out = BOX / 'outputs' / 'verification.wav'
            out.parent.mkdir(exist_ok=True)
            out.write_bytes(wav)
            report.update(wav=str(out), audio_seconds=len(samples)/rate, sample_rate=rate)
        report['ok'] = True
    except Exception as exc:
        report['error'] = str(exc)
        raise
    finally:
        if proc.poll() is None:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'], capture_output=True)
        proc.wait(timeout=20)
        report['elapsed_seconds'] = round(time.monotonic()-start, 2)
        (BOX / 'logs' / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__': main()
