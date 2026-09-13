# Irodori TTS Box

Windows 向けの Irodori-TTS 実行環境と、Irodori 対応 VOICEVOX Editor をまとめるためのソースリポジトリです。GPU を自動判定して CUDA、DirectML (Radeon)、または CPU バックエンドを構成します。

このリポジトリは**ソース配布用**です。モデル重み、話者埋め込み、生成音声、ログ、ローカル仮想環境、ビルド済み実行ファイルは含めません。

## 必要なもの

- Windows 10/11
- Python 3.11（セットアップで必要に応じて取得）
- `uv` は初回セットアップ時に `.local\\bin` へ公式インストーラーから取得されます。
- Node.js と pnpm はセットアップ時に `.local` へ取得されます。
- NVIDIA GPU（CUDA）または AMD Radeon GPU（DirectML）は任意。CPU でも利用可能です。

## セットアップと起動

リポジトリのルートで次を実行します。初回セットアップは GPU を検出し、必要な Python 環境と依存関係を `.local` に作成します。

```bat
bat\first_setup.bat
rebuild_and_open_editor.bat
```

`rebuild_and_open_editor.bat` は Editor をソースからビルドして起動します。バックエンドを指定する場合は、たとえば `bat\first_setup.bat -Backend cuda` を使います。利用できる引数は `bat\first_setup.bat -Help` で確認できます。

モデルは初回利用時に設定された Hugging Face の配布元から取得されます。モデルカードのライセンスと利用条件を確認したうえで使ってください。話者埋め込みを使う場合は、権利者の許諾を得た自作または配布許可済みのものだけを `speakers` に置いてください。

## 構成

```text
bat/                Windows 用セットアップ・起動スクリプト
irodori-tts/        Irodori API 用ラッパーとテスト
runtime/trt-lab/    Irodori-TTS ランタイムのソース
tools/              セットアップ・検証用ユーティリティ
voicevox-editor/    Irodori 対応 VOICEVOX Editor のソース
models/             モデル配置場所（重みは Git 管理外）
speakers/           話者データ配置場所（Git 管理外）
```

## 開発時の確認

Python 環境を構成済みの場合、音声 I/O の確認は次で行えます。

```powershell
.\.local\venv\Scripts\python.exe tools\test_audio_io.py
```

配布環境の簡易検証には `bat\verify.bat` を使います。生成物とログは `outputs/` と `logs/` に保存され、Git には追加されません。

## ライセンスと第三者コンポーネント

ライセンス境界、上流プロジェクト、モデル・話者データの扱いは [NOTICE.md](NOTICE.md) を必ず確認してください。特に `voicevox-editor/` の改変・再配布には LGPL-3.0 の条件が適用されます。
