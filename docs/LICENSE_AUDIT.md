# ライセンス表示の確認（2026-09-15）

`NOTICE.md` は配布物向けの説明です。ヘルプ画面のデータではありません。
「ヘルプ → ライセンス情報」は次のファイルを読み込みます。

| データ | 内容 | 更新方法 |
| --- | --- | --- |
| `voicevox-editor/public/licenses.json` | プロジェクト・標準モデルの説明、著作者、条件 | 使用モデルを変更したときに一次情報を確認して編集 |
| `voicevox-editor/public/dependency-licenses.json` | pnpm の本番依存関係（間接依存を含む）、7-Zip、Electron | Editor 内で `pnpm run license:dependencies`。postinstall 時にも更新 |
| `voicevox-editor/public/runtime-licenses.json` | Python パッケージの LICENSE・NOTICE、Python・Node.js | `.local\venv\Scripts\python.exe tools\generate_runtime_licenses.py`。Radeon は `--site-packages work\amd-dml-venv\Lib\site-packages` を追加 |

エンジン側のライセンス画面も共通のモデル・実行環境データを使用します。
収集時に本文が見つからない依存関係は生成を失敗させ、誤ったライセンスで補完しません。
wheel/npm に本文がない既知の依存関係は `licenses/` に保存した一次資料で補完します。
取得元は `licenses/sources.json` に記録しています。更新時は適用バージョンとの整合も確認してください。

## 主な表示漏れと対応

- Parakeet TDT-CTC 0.6B Japanese: NVIDIA の元モデルは CC BY 4.0。
  著作者、元モデルと変換版の取得元、ONNX/int8 変換の表示、ライセンスへのリンクを追加。
- Irodori-TTS-v4.1-Small: コードとは別にモデルの MIT 表記とモデルカードの Ethical Restrictions を追加。
- ModernBERT-ja-310m: 標準チェックポイントが使うエンコーダー・トークナイザー。SB Intuitions の MIT 本文を追加。
- Semantic-DACVAE-Japanese-32dim: 日本語調整版の MIT 表記、取得リビジョンとモデルカードを追加。
- DACVAE のコード: インストールする固定コミットの LICENSE は Apache-2.0。モデルの MIT と区別。
- sherpa-onnx、PyTorch、Transformers、ONNX Runtime、SoundFile などの直接・間接依存を追加。
- セットアップ用の uv は MIT / Apache-2.0 の選択ライセンス。両方の本文を追加。
- Vue、Quasar、PixiJS などと、間接依存を追加。従来の収集処理では pnpm の直接依存27件しか得られなかったため、pnpm の依存グラフを使用。
- VOICEVOX Editor は本文参照の案内だけだったため、同梱 LGPL 本文も画面で読めるように変更。

## 表示だけでは解決しない確認事項

1. **SoundFile のネイティブ依存、soxr、7-Zip には LGPL 等の条件がある。**
   SoundFile wheel 内の libsndfile の COPYING と `licensing/license_notes.md`、
   7-Zip の同梱 License.txt を収集した。バイナリを再配布する場合は対応するソース、
   再リンク・差し替え等の義務も配布形態に応じて確認する。
2. **DACVAE 上流重みの表記に不一致がある。**
   `facebook/dacvae-watermarked` のメタデータは Apache-2.0、本文は SAM License と記載し、
   LICENSE リンク先は取得できなかった。日本語調整版の MIT 表記だけを根拠に、上流由来部分の
   条件まで解決済みとは扱わない。コードの固定コミットの Apache-2.0 本文は確認済み。
   https://huggingface.co/facebook/dacvae-watermarked
3. **Electron の Chromium 通知は別ファイル。** Electron 本体の MIT はヘルプに掲載。
   全文の `LICENSES.chromium.html` は Electron 配布物に付属するので、バイナリ配布時に保持する。
4. **対象は現在の標準モデルとローカルの CPU/Radeon 環境。** 未インストールの CUDA/TensorRT、
   外部 FFmpeg、別途導入するモデル・話者・画像の全条件まで確認したものではない。
   TensorRT 等を追加・配布するときは、その版の契約条件とネイティブ依存の通知を別途確認する。

この一覧は表示漏れの調査結果であり、配布物全体の法的適合性を保証するものではありません。
