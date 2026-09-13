"""ASR のトークン時刻から、セリフ文字ごとの時間アンカーを作る。

口パクのタイムラインは、セリフの文字数から比例配分すると数十ミリ秒ずれる。
ここでは生成音声を ASR（sherpa-onnx / Parakeet TDT CTC 0.6B JA int8）へ通し、
「どの文字がいつ発話されたか」を実測してタイムラインの基準にする。

- ASR はあくまで時刻の取得用。文字の対応は入力セリフ（既知）を正とする。
- モデルが無いときは初回利用時に自動で取得する（`ensure_asr_model`）。
  取得に失敗した場合だけ available=False を返し、呼び出し側は推定へ戻す。
"""
from __future__ import annotations

import base64
import io
import os
import threading
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent  # irodori-tts
BOX_ROOT = ROOT.parent
MODEL_DIR = Path(os.environ.get("IRODORI_ASR_DIR", str(BOX_ROOT / "models" / "asr")))
MODEL_FILE = MODEL_DIR / "model.int8.onnx"
TOKENS_FILE = MODEL_DIR / "tokens.txt"

# 初回利用時に取得するモデル（sherpa-onnx の Parakeet TDT CTC 0.6B JA int8）。
# 取得元はリビジョン固定。差し替えたいときは環境変数で上書きする。
ASR_REPO = os.environ.get(
    "IRODORI_ASR_REPO",
    "csukuangfj/sherpa-onnx-nemo-parakeet-tdt_ctc-0.6b-ja-35000-int8")
ASR_REVISION = os.environ.get(
    "IRODORI_ASR_REVISION",
    "bef18eb066808c90bd0f5df5be685767b0732de8")
ASR_FILES = {"model.int8.onnx": 655_542_604, "tokens.txt": 28_557}

_download_lock = threading.Lock()
_download_thread: threading.Thread | None = None
_download_error: str | None = None


def model_ready(folder: Path | None = None, files: dict | None = None) -> bool:
    """必要なファイルが想定サイズで揃っているか。"""
    folder = Path(folder or MODEL_DIR)
    files = files or ASR_FILES
    for name, size in files.items():
        target = folder / name
        if not target.is_file() or target.stat().st_size != size:
            return False
    return True


def _fetch(folder: Path, files: dict, progress=None, log=None) -> None:
    from huggingface_hub import hf_hub_download

    folder.mkdir(parents=True, exist_ok=True)
    total = len(files)
    for index, (name, size) in enumerate(files.items(), start=1):
        target = folder / name
        if target.is_file() and target.stat().st_size == size:
            continue
        percent = int(5 + 80 * (index - 1) / max(total, 1))
        if progress:
            progress(f"ASRモデルを取得中: {name}", percent)
        if log:
            log(f"ASR model download: {name} ({size} bytes) from {ASR_REPO}@{ASR_REVISION[:12]}")
        hf_hub_download(ASR_REPO, name, revision=ASR_REVISION, local_dir=str(folder))
        actual = target.stat().st_size if target.is_file() else 0
        if actual != size:
            raise RuntimeError(
                f"{name} のサイズが想定と違います（{actual} != {size}）。取得をやり直してください")
    if progress:
        progress("ASRモデルの取得完了", 90)


def ensure_asr_model(progress=None, log=None, wait_seconds: float = 0.0,
                     folder: Path | None = None, files: dict | None = None) -> dict:
    """モデルが無ければ取得する。

    ダウンロードは専用スレッドで走らせ、`wait_seconds` 秒だけ待って状態を返す。
    待ち切れなくても取得は続くので、次の呼び出しで揃っていれば使える。
    """
    global _download_thread, _download_error

    folder = Path(folder or MODEL_DIR)
    files = files or ASR_FILES
    if model_ready(folder, files):
        return {"ready": True, "pending": False, "error": None, "folder": str(folder)}

    with _download_lock:
        if _download_thread is None or not _download_thread.is_alive():
            _download_error = None

            def run():
                global _download_error
                try:
                    _fetch(folder, files, progress, log)
                except Exception as exc:  # noqa: BLE001
                    _download_error = str(exc)
                    if log:
                        log(f"ASR model download failed: {exc}")
                    if progress:
                        progress("ASRモデルの取得に失敗", 0, False)

            _download_thread = threading.Thread(target=run, name="asr-model-fetch", daemon=True)
            _download_thread.start()
        thread = _download_thread

    if wait_seconds:
        thread.join(timeout=float(wait_seconds))
    ready = model_ready(folder, files)
    if ready and progress:
        progress("ASRモデルの取得完了", 100, False)
    return {"ready": ready, "pending": thread.is_alive(), "error": _download_error,
            "folder": str(folder)}


def asr_package_error() -> str:
    """sherpa-onnx 未導入時に出す案内。"""
    return ("sherpa-onnx が入っていません。"
            "uv pip install --python .local\\venv\\Scripts\\python.exe -r tools\\requirements-asr.txt "
            "を実行してから、もう一度読み込んでください")


SAMPLE_RATE = 16000
FRAME_SECONDS = 0.08  # FastConformer の 8x サブサンプリング（10ms hop）

# 時刻を持たない文字（句読点・記号）は前後の文字から補間する
_PUNCTUATION = set(" 　、。，．！？!?,.・:;；「」『』（）()[]{}〈〉《》…‥~〜ー-―—’‘“”\"'+=*/\\|@#$%^&_`")


def to_hiragana(char: str) -> str:
    code = ord(char)
    if 0x30A1 <= code <= 0x30F6:
        return chr(code - 0x60)
    if char == "ン":
        return "ん"
    if char == "ッ":
        return "っ"
    return char


def normalize(text: str) -> str:
    out = []
    for char in text:
        if char in _PUNCTUATION or char.isspace():
            continue
        out.append(to_hiragana(char))
    return "".join(out)


def _align(reference: str, hypothesis: str) -> list[int | None]:
    """文字列の単調アラインメント。reference[i] に対応する hypothesis の位置を返す。"""
    n, m = len(reference), len(hypothesis)
    if n == 0 or m == 0:
        return [None] * n
    # Levenshtein のコスト表（メモリを抑えるため2行）＋バックトラック用に全行を保持
    previous = list(range(m + 1))
    rows = [previous]

    for i in range(1, n + 1):
        current = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
            current[j] = min(
                previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost
            )
        rows.append(current)
        previous = current
    mapping: list[int | None] = [None] * n
    i, j = n, m
    while i > 0 and j > 0:
        cost = 0 if reference[i - 1] == hypothesis[j - 1] else 1
        if rows[i][j] == rows[i - 1][j - 1] + cost:
            if cost == 0:
                mapping[i - 1] = j - 1
            i -= 1
            j -= 1
        elif rows[i][j] == rows[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1
    return mapping


def decode_wav(payload: bytes) -> np.ndarray:
    """WAV(bytes) を 16kHz モノラルの float32 へ。

    Python の wave モジュールは float32 WAV（この箱の生成音声）を読めないので、
    RIFF チャンクを自前で走査する。
    """
    if payload[:4] != b"RIFF" or payload[8:12] != b"WAVE":
        raise ValueError("not a RIFF/WAVE payload")
    offset = 12
    fmt: dict | None = None
    data: bytes | None = None
    while offset + 8 <= len(payload):
        chunk_id = payload[offset : offset + 4]
        size = int.from_bytes(payload[offset + 4 : offset + 8], "little")
        body = payload[offset + 8 : offset + 8 + size]
        if chunk_id == b"fmt ":
            fmt = {
                "format": int.from_bytes(body[0:2], "little"),
                "channels": int.from_bytes(body[2:4], "little"),
                "rate": int.from_bytes(body[4:8], "little"),
                "bits": int.from_bytes(body[14:16], "little"),
            }
        elif chunk_id == b"data":
            data = body
        offset += 8 + size + (size % 2)
    if fmt is None or data is None:
        raise ValueError("WAV is missing fmt/data chunk")

    channels = max(1, fmt["channels"])
    bits = fmt["bits"]
    audio_format = fmt["format"]
    if audio_format == 3 or (audio_format == 0xFFFE and bits == 32):
        samples = np.frombuffer(data, dtype="<f4").astype(np.float32)
    elif bits == 16:
        samples = np.frombuffer(data, dtype="<i2").astype(np.float32) / 32768.0
    elif bits == 32:
        samples = np.frombuffer(data, dtype="<i4").astype(np.float32) / 2147483648.0
    elif bits == 8:
        samples = (np.frombuffer(data, dtype="u1").astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported WAV format: {audio_format} / {bits} bit")
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    rate = fmt["rate"]
    if rate != SAMPLE_RATE:
        samples = resample(samples, rate, SAMPLE_RATE)
    return np.ascontiguousarray(samples, dtype=np.float32)


def resample(samples: np.ndarray, source_rate: int, target_rate: int) -> np.ndarray:
    """整数比は間引き＋平均、それ以外は線形補間。ASR の入力用なので十分。"""
    if source_rate == target_rate:
        return samples
    try:
        from scipy.signal import resample_poly  # type: ignore

        from math import gcd

        divisor = gcd(int(source_rate), int(target_rate))
        return resample_poly(
            samples, target_rate // divisor, source_rate // divisor
        ).astype(np.float32)
    except Exception:
        length = int(round(samples.size * target_rate / source_rate))
        if length <= 0:
            return np.zeros(0, dtype=np.float32)
        source_positions = np.linspace(0.0, samples.size - 1, num=samples.size)
        target_positions = np.linspace(0.0, samples.size - 1, num=length)
        return np.interp(target_positions, source_positions, samples).astype(np.float32)


class AsrTimeline:
    """sherpa-onnx の recognizer を遅延ロードして使い回す。"""

    def __init__(self, model: Path = MODEL_FILE, tokens: Path = TOKENS_FILE, threads: int = 0):
        self.model = Path(model)
        self.tokens = Path(tokens)
        self.threads = threads or max(2, (__import__("os").cpu_count() or 4) // 4)
        self._recognizer = None
        self._lock = threading.Lock()
        self._error: str | None = None
        self.last_seconds: float | None = None

    @property
    def available(self) -> bool:
        return self.model.exists() and self.tokens.exists()

    def status(self) -> dict:
        return {
            "available": self.available,
            "loaded": self._recognizer is not None,
            "model": self.model.name,
            "sampleRate": SAMPLE_RATE,
            "resolution": FRAME_SECONDS,
            "error": self._error,
            "lastSeconds": self.last_seconds,
        }

    def _ensure(self):
        if self._recognizer is not None:
            return self._recognizer
        if not self.available:
            raise RuntimeError(f"ASR model not found: {self.model}")
        import sherpa_onnx

        self._recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
            model=str(self.model),
            tokens=str(self.tokens),
            num_threads=max(1, int(self.threads)),
            sample_rate=SAMPLE_RATE,
            feature_dim=80,
            decoding_method="greedy_search",
        )
        return self._recognizer

    def transcribe(self, samples: np.ndarray) -> dict:
        recognizer = self._ensure()
        stream = recognizer.create_stream()
        stream.accept_waveform(SAMPLE_RATE, samples)
        recognizer.decode_stream(stream)
        result = stream.result
        return {
            "text": result.text,
            "tokens": list(getattr(result, "tokens", []) or []),
            "timestamps": [float(t) for t in (getattr(result, "timestamps", []) or [])],
        }

    def anchors(self, text: str, samples: np.ndarray) -> dict:
        """入力セリフの文字ごとに (char, start, end) を返す。"""
        import time

        started = time.perf_counter()
        asr = self.transcribe(samples)
        self.last_seconds = round(time.perf_counter() - started, 2)

        reference = normalize(text)
        # ASR トークンは複数文字を含むことがあるので、文字単位へ展開する
        hypothesis_chars: list[str] = []
        hypothesis_times: list[float] = []
        for token, timestamp in zip(asr["tokens"], asr["timestamps"]):
            for char in normalize(token):
                hypothesis_chars.append(char)
                hypothesis_times.append(float(timestamp))
        if hypothesis_chars:
            # 最後の文字の終端はトークンの次の時刻（無ければ +1フレーム）
            hypothesis_times.append(hypothesis_times[-1] + FRAME_SECONDS)

        mapping = _align(reference, "".join(hypothesis_chars))
        anchors: list[dict] = []
        for index, char in enumerate(reference):
            position = mapping[index]
            if position is not None:
                start = hypothesis_times[position]
                end = (
                    hypothesis_times[position + 1]
                    if position + 1 < len(hypothesis_times)
                    else start + FRAME_SECONDS
                )
            else:
                # 対応が取れない文字は前後から補間する
                previous = next(
                    (
                        anchors[i]["end"]
                        for i in range(len(anchors) - 1, -1, -1)
                        if anchors[i].get("end") is not None
                    ),
                    None,
                )
                following = None
                for later in range(index + 1, len(reference)):
                    position_later = mapping[later]
                    if position_later is not None:
                        following = hypothesis_times[min(position_later, len(hypothesis_times) - 1)]
                        break
                if previous is None and following is None:
                    start, end = 0.0, FRAME_SECONDS
                elif previous is None:
                    start, end = max(0.0, following - FRAME_SECONDS), following  # type: ignore[operator]
                elif following is None:
                    start, end = previous, previous + FRAME_SECONDS
                else:
                    start, end = previous, max(previous, following)
            anchors.append({"char": char, "start": round(start, 3), "end": round(end, 3)})
        return {
            "text": text,
            "asrText": asr["text"],
            "anchors": anchors,
            "resolution": FRAME_SECONDS,
            "audioSeconds": round(samples.size / SAMPLE_RATE, 3),
            "asrSeconds": self.last_seconds,
        }


_DEFAULT: AsrTimeline | None = None


def default_timeline() -> AsrTimeline:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = AsrTimeline()
    return _DEFAULT
