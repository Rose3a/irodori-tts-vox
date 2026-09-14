# 貢献者ガイドライン

Irodori-TTS Vox への提案や不具合報告は、[Rose3a/irodori-tts-vox](https://github.com/Rose3a/irodori-tts-vox) で受け付けます。VOICEVOX公式の窓口へは送らないでください。

## 報告に含める情報

- 実行したバッチファイルまたは操作手順
- CPU、CUDA、TensorRT、DirectMLのどの実行モードか
- OSとIrodori-TTS Voxのバージョン
- 再現手順、期待した結果、実際の結果
- 関係するログ（ユーザー名やローカルパスなどを除いてください）

## 変更を提案する場合

1. 変更理由と対象範囲を明確にします。
2. 関係するPythonテスト、エディタの単体テスト、型チェックを実行します。
3. 上流VOICEVOX由来の著作権表示とライセンス通知を維持します。
4. モデルや話者データなど、リポジトリへ収録できないファイルをコミットしないでください。

開発環境と検証方法は、ルートの `README.md` と `docs/TESTING.md` を参照してください。
