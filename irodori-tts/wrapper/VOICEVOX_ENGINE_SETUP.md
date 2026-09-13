# 公式VOICEVOXエディタでIrodoriを使う

`voicevox_engine.py` は公式VOICEVOXエディタが使うEngine APIの互換サーバーです。
公式エディタ本体を改造せず、バックエンドごとに別ポートで起動します。

```bat
wrapper\run_voicevox_engine.bat cpu 50021
wrapper\run_voicevox_engine.bat cuda 50022
wrapper\run_voicevox_engine.bat trt 50023
wrapper\run_voicevox_engine.bat radeon 50024
```

公式エディタのエンジン設定に次のホストを登録します。Engineの起動は、PC固有のドライブ文字を使わず、プロジェクトのルートフォルダを基準にした `wrapper\run_voicevox_engine.bat` を実行してください。

| 表示名 | URL | 用途 |
|---|---|---|
| Irodori CPU | `http://127.0.0.1:50021` | CPU PyTorch |
| Irodori CUDA | `http://127.0.0.1:50022` | CUDA PyTorch |
| Irodori TensorRT | `http://127.0.0.1:50023` | TensorRT |
| Irodori Radeon | `http://127.0.0.1:50024` | AMD DirectML |

同じ話者カセットが各エンジンに表示されるため、公式GUI上でエンジンを切り替えて速度と音質を比較できます。デフォルトの推論ステップはモデル依存で、RFモデルは8、MeanFlowモデルは4です（後述の「MeanFlow（4ステップ）モデル」）。

Irodori専用の簡易GUIも用意しています。公式Engine APIへ接続するため、同じ話者カセットとバックエンドを使えます。

公式VOICEVOX Editorは、同梱のEditor実行ファイルから起動します。

この画面では台本、話者カセット、バックエンド、step、seed、音声長、話速、CFG、生成履歴、再生を扱います。生成履歴で項目を選び「選択した1件を再生」を押せば、連続生成ではなくその音声だけを再生できます。モーラ・ピッチ編集は表示しません。GPU使用率はNVIDIA環境では `nvidia-smi` から表示します。

## 現在の対応範囲

- `/speakers`, `/audio_query`, `/synthesis`, `/version`, `/engine_manifest.json`
- 話者カセット (`*.speaker.safetensors`) の一覧
- WAV合成と公式エディタへの返却
- `speedScale` はIrodoriの`duration_scale`に変換
- `irodori_cfg_speaker` / `irodori_cfg_caption` でCFGを指定可能（RFモデルのみ）
- MeanFlowモデルは既定4ステップ・CFG/スケジュール無効で送信（自動判定）

## MeanFlow（4ステップ）モデル

モデル種別はチェックポイントの `config_json.flow_parameterization` から自動判定します。`meanflow` のときは:

- 既定ステップ数が4（RFは8）。クエリが `irodori_steps` を明示したときだけその値を使います
- CFGスケールとSway Samplingは送りません（0 / `linear`）。CFGは蒸留時に教師の軌跡へ融合済みで、推論時のCFG分岐とスケジュールは効かないためです
- 判定結果は起動ログの `flow=` と `default_steps=`、`/engine_manifest.json` の `irodori_flow_parameterization` / `irodori_flow_parameterization_source` / `irodori_default_steps` で確認できます
- 合成ごとに `[voicevox] synth: flow=... steps=... cfg=... schedule=...` がstderrへ出ます

MFチェックポイントを使うときは、起動前に `IRODORI_CHECKPOINT` を設定してください。未設定なら `models\model.safetensors` を使います。

```bat
set "IRODORI_CHECKPOINT=%CD%\.cache\huggingface\hub\models--Aratako--Irodori-TTS-v4.1-Small-MF\snapshots\<snapshot>\model.safetensors"
wrapper\run_voicevox_engine.bat cpu 50021
```

IrodoriにはVOICEVOXのアクセント句・モーラ編集データがないため、音声クエリのテキストは保持しますが、公式GUIのモーラ単位編集はまだ空になります。話速は適用されますが、ピッチ・イントネーションは今のIrodoriランタイムに対応する制御点がないため保留です。

## Radeonについて

Radeonは`work\amd-dml-venv`のDirectML Pythonと`work\codec_decoder.onnx`を使います。FP32の拡散推論に加え、可変長の音声デコードもDirectMLで実行します。参照音声のエンコードはCPUです。初期設定は拡散8 stepです（MeanFlowモデルなら4 step）。

コーデックは通常のIrodoriランタイムと同じモノラル出力経路を使うversion 2が必要です。旧版の8フレーム書き出しは起動時に拒否します。プロジェクトのルートで、アプリ用Pythonを使って再生成してください。

```powershell
& .local\venv\Scripts\python.exe tools\export_radeon_codec.py
```

既存のONNXはバックアップし、複数の入力長でCPU版との一致検証が通ってから置き換えます。再生成後はエンジンを再起動してください。DirectMLが利用できない場合や未対応グラフの場合、音声デコードをCPUへ黙って置き換えずエラーを返します。

実際の文章での合成・CPU版との波形比較は`tools\verify_radeon_decode.py`をアプリ用Pythonで実行できます。結果と比較用WAVは`work\radeon-decode-validation`に保存します。
