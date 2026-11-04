# PUA字形見本の版不一致と描画検証

2026-11-04調査。採用PUA表は1.473版ですが、公式リンクから取得したフォントを確認すると版が一致しませんでした。

| 入力 | 実バイトの確認結果 |
| --- | --- |
| PUA HTML・IDS_PUA.TXT | 1.473表示、6,030識別子 |
| 公式TTF | 内部名 `Version 1.472`、2025-07-07、PUA 6,024字 |
| 公式WOFF | 内部名 `Version 1.472`、PUA 6,024字 |
| 公式WOFF2 | 内部名 `Version 1.472`、PUA 6,024字 |

TTFのSHA-256は `92e7155bd28f5570449f4dc71e9bb6fa919f67ef0120d4f83b58c61bed3ed4dc`。取得時の期待版と内部確認版を分けて記録しました。[TTF記録](../review-sources.lock.json)、[Webフォント記録](../review-webfonts.lock.json)、[メタデータ](pua-font-metadata.json)

表に存在してTTFにないのはU+E87B、E87C、E87D、E87F、F55A、F55Bの6件です。[原資料の行](pua-font-missing.json)。この不一致を解消するまで、TTFを1.473版の正解字形として利用しません。候補台帳を1.472版へすり替えることもしません。

## 診断的な比較

出典ID候補のあるPUA識別子から、並び順に等間隔で12件を抽出し、各先頭候補を描画しました。左にTTF 1.472、右にKAGEを配置し、版不一致を画像内に明記しています。各字形の外接矩形へ合わせて表示し、縦横比は保持します。書体の太さ・うろこ・字面位置を同一に補正する処理はしていません。

12例の目視では大きな部品配置は類似して見えますが、線の形や部品の比率に差があります。これは1.473版の確認済み対応とはしません。[診断記録](diagnostic-review.json)。画像と比較用bundleは `data/generated/review/` に保存しており、公開配布物にはまだ含めていません。

## 全PUA候補の描画検査

出典IDで発見した全2,406字形の固定版と依存KAGEを、`@kurgm/kage-engine` 0.7.0で描画しました。全2,406件で有限座標を持つ空でないポリゴン出力を確認しました。[検査入力](pua-render-input.json)、[結果](pua-render-summary.json)

これは描画出力の検査です。命令の一部がエンジン内で無視されていないこと、可読性、正しい地域字形、PUAとの同一性を証明するものではありません。対応表の字形レビュー状態は変えていません。

## 再現方法

```powershell
python -m kanji_kage_map restore --lock review-sources.lock.json
python -m kanji_kage_map restore --lock review-webfonts.lock.json
python -m pip install --target .cache/review -r requirements-review.txt
npm ci --ignore-scripts
python tools/review_font.py
python tools/prepare_review.py
node tools/render_bundles.mjs data/generated/review/bundles.json data/generated/review/rendered.json
python tools/review_sheet.py
python tools/prepare_pua_render.py
node tools/render_bundles.mjs data/generated/review/pua-all-bundles.json data/generated/review/pua-all-rendered.json
node --test tests/render.test.mjs
```

`prepare_review.py` と比較シートは今回の不一致を調べる診断用です。1.473版一致を主張するレビューには使えません。上流フォントが更新されると `restore` はハッシュ不一致を報告するため、別lockで新しく取得・版確認を行ってください。

## ライセンスの区別

- GlyphWikiのKAGEデータ：[dumpのライセンス](../licenses/GLYPHWIKI.txt)。
- KAGE描画エンジン：パッケージのGPL-3.0表示と同梱COPYINGを確認。[全文](../licenses/KAGE-ENGINE-GPL-3.0.txt)、[版・ハッシュ](engine-source.json)。任意の描画ラッパーもGPL-3.0-onlyとして明記。
- 取得TTF：nameテーブルID13のARPHIC PUBLIC LICENSEを確認・抽出。[全文](../licenses/ARPHICPL.txt)。これはIDSやPUAの説明表に自動適用しません。
- BabelStone IDS：原本ヘッダの利用・権利宣言は既に確認。別資料であるPUA表・IDS_PUAの再配布条件はなお整理中。

フォント本体、依存パッケージ、生成画像はGitから除外しています。独自Pythonコードの公開ライセンス、配布物一覧、PUA資料を含む公開条件の確定は残作業です。
