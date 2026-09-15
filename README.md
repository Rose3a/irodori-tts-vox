
# kataribe

Windows 向けの Irodori-TTS 実行環境と、Irodori 対応 VOICEVOX Editor のリポジトリです。
環境の GPU を自動判定し、CUDA / DirectML (Radeon) / CPU の各バックエンドを構成します。

※モデルの重みファイル、話者データ、生成音声、仮想環境などはリポジトリに含まれません（セットアップ時に自動取得、または手動配置）。

## 動作要件

- Windows 10 / 11
- NVIDIA GPU（CUDA）または AMD Radeon GPU（DirectML）※CPUのみでも動作可能

Python 3.11、uv、Node.js、pnpm などのツール類は、初回セットアップ時に `.local` ディレクトリへ自動的にダウンロード・配置されます。

## セットアップと起動

初めて使う場合は、Git を使うなら次のように clone します。Git を使わない場合は、GitHub の「Code」から ZIP をダウンロードして展開してください。

```powershell
git clone https://github.com/Rose3a/kataribe.git
cd kataribe
```

展開または clone したリポジトリのルートで `setup.bat` を一度実行します。GPU の検出と、`.local` 配下への環境構築が行われます。完了後は `open_browser.bat` でブラウザ版を起動します。

```bat
setup.bat
open_browser.bat
```

### TensorRTによる高速化（CUDA環境）

`setup.bat` の完了後、対応する CUDA 環境では `bat\trt_setup.bat` を実行することで、TensorRT による推論の高速化を利用できます。

```bat
bat\trt_setup.bat
```

> **注意:** すべての CUDA 対応 GPU での動作を保証するものではありません。未確認の環境もあります。
>
> **動作確認済み環境:** RTX 3060（MFモデル / step4）では、約20秒の音声を1秒未満で推論できることを確認しています。

通常は `open_browser.bat` を使用してください。ブラウザ版のエディタとエンジンを起動します。

Electron Editor をソースからビルドして起動する場合は `bat\rebuild_and_open_editor.bat` を使用します。

- バックエンドを手動指定する場合: `bat\first_setup.bat -Backend cuda`
- 指定可能なオプションの確認: `bat\first_setup.bat -Help`

※モデルは初回実行時に Hugging Face から自動ダウンロードされます。各モデルの利用規約を確認の上で使用してください。
※話者データを利用する場合は、権利関係に問題のないデータのみを `speakers/` に配置してください。

## ディレクトリ構成

```text
bat/                セットアップ・起動用バッチファイル
irodori-tts/        Irodori API ラッパーおよびテスト
runtime/trt-lab/    Irodori-TTS ランタイム本体
tools/              セットアップ・検証用スクリプト
voicevox-editor/    Irodori 対応 VOICEVOX Editor ソース
models/             モデル配置ディレクトリ（git管理外）
speakers/           話者データ配置ディレクトリ（git管理外）
```

## 開発・検証

### 音声 I/O のテスト
```powershell
.\.local\venv\Scripts\python.exe tools\test_audio_io.py
```

### 簡易動作確認
```bat
bat\verify.bat
```
※出力音声やログは `outputs/` および `logs/` に保存されます（git管理外）。

### 単体テスト
標準の `unittest` を使用しているため、pytest は不要です。
```powershell
.\.local\venv\Scripts\python.exe -m unittest discover -s irodori-tts\tests -t irodori-tts\tests -p "test_*.py"
```

WebUI 経由のテスト（セッショントークン、`/audio_query`、`/synthesis`）や、ヘッドレスブラウザでの描画テストの詳細は [docs/TESTING.md](docs/TESTING.md) を参照してください。

### セットアップスクリプトについて

- **`setup.bat`（通常はこちらを使用）**:
  `bat\first_setup.bat` を呼び出し、GPU 判定から `.local` への環境構築を一括で行います。
- **`bat\first_setup.bat`**:
  `tools\setup.ps1` を呼び出し、GPU 判定から `.local` への環境構築（Python / Node / 依存関係 / モデル準備）を一括で行います。`bat\launch.bat` や `bat\serve_browser.bat` はこの環境を参照します。
- **`irodori-tts\setup_venv.bat`**:
  ラッパー単体を `irodori-tts\.venv` で動かすためのレガシーなスクリプトです。依存関係の構成が異なるため、通常は使用しません。

## ライセンス・クレジット

ライセンスの適用範囲、上流プロジェクト、モデルや話者データの取り扱いについては [NOTICE.md](NOTICE.md) を確認してください。
`voicevox-editor/` の改変・再配布には LGPL-3.0 が適用されます。詳細は [LICENSE](LICENSE) を参照してください。
