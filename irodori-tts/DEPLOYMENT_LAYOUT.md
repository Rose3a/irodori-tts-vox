# Irodori-TTS 配布レイアウト

配布時はフロントエンドとバックエンドを同じルートに置く。

```text
Irodori-TTS/
  frontend/                 # kataribe の Electron アプリ
    kataribe.exe
    irodori-engine-path.txt
  backend/                  # このプロジェクトの実行環境
    .venv/
    wrapper/
    models/
    embeddings/
    bf16-fallback/
    runtime/
    outputs/
```

`frontend/irodori-engine-path.txt` には `..\backend` を指定する。バックエンドを別の場所に置く場合は絶対パスも指定できる。フロントエンドはモデル・話者ファイルを保持せず、バックエンドのフォルダを読む。

話者埋め込みは `backend/embeddings/<speaker>.speaker.safetensors` に置く。サムネイルは同じ場所に `<speaker>.png`、`<speaker>.jpg`、`<speaker>.webp` のいずれかを置く。VOICEVOX APIの `/speakers` と `/speaker_info` が同じ画像を返すため、Torch・TensorRT・Electron UIで共通になる。

Torchで追加した話者をTensorRT用に変換する作業は不要。TorchとTensorRTは同じsafetensors埋め込みを読む。TensorRTは話者をGPU用の一時キャッシュへコピーしてplanを再ロードせずに切り替える。新しいファイルを置いた後はUIの「一覧を更新」を押す。

TensorRTのplan自体はGPU・TensorRTバージョン依存なので、話者追加では再構築不要だが、モデル本体を交換した場合はplanを作り直す。

## 口パク用のASRモデル（初回利用時に自動取得）

`/irodori/timeline` はセリフ文字ごとの発話時刻を作るために、sherpa-onnx 形式のオフラインASRを使う。モデルは配布物に含まれず、**初回利用時にエンジンが自動で取得**して次へ置く。

```text
models/asr/model.int8.onnx
models/asr/tokens.txt
```

- 取得元は `irodori-tts/wrapper/asr_timeline.py` の `ASR_REPO` / `ASR_REVISION`（リビジョン固定）。`IRODORI_ASR_REPO` / `IRODORI_ASR_REVISION` で上書きできる。
- 665MB ほどあるので、初回の要求は取得を待って 45 秒で切り上げる（`IRODORI_ASR_WAIT_SECONDS`）。待ち切れても取得は続くので、もう一度読み込むと揃っている。
- 進捗はエンジンの進捗表示とログに出る。手動で置いてもよい（フォルダを変える場合は `IRODORI_ASR_DIR`）。
- 取得を止めたい場合は `IRODORI_ASR_AUTO_DOWNLOAD=0`。
- 認識器の依存は `sherpa-onnx`。セットアップ環境には `tools/requirements-app.txt` 経由で入る。入っていない環境では
  `uv pip install --python .local\venv\Scripts\python.exe -r tools\requirements-asr.txt` を実行する。
- モデルが無い場合、この機能は「利用不可」を返すだけで、音声生成そのものは動く。
