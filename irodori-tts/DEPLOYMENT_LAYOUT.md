# Irodori-TTS 配布レイアウト

配布時はフロントエンドとバックエンドを同じルートに置く。

```text
Irodori-TTS/
  frontend/                 # Irodori VOICEVOX Editor の Electron アプリ
    Irodori VOICEVOX Editor.exe
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

## 口パク用のASRモデル（任意）

`/irodori/timeline` はセリフ文字ごとの発話時刻を作るために、sherpa-onnx 形式のオフラインASRを使う。モデルは配布物に含まれないので、使う場合だけ次を置く。

```text
models/asr/model.int8.onnx
models/asr/tokens.txt
```

sherpa-onnx が配布するオフライン認識モデル（Parakeet TDT 系の int8 変換など、`model.int8.onnx` と `tokens.txt` を持つもの）を入手して配置する。フォルダを変える場合は `IRODORI_ASR_DIR` を設定する。ファイルが無い場合、この機能は「利用不可」を返すだけで、音声生成そのものは動く。
