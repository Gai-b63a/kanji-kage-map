# 「一」の日本典拠に対する構造比較

2026-11-04、CodexによるAI目視レビュー。U+4E00の固定KAGE `u4e00@46` と、Unicode 18.0公式コード表の日本典拠J0-306Cを比較しました。比較した全字形について `structural_glyph_v1` の構造一致と判断しました。これは一文字・一候補版・一典拠に限定した判断です。

## 一次資料と比較対象

- [公式コード表](https://www.unicode.org/Public/18.0.0/charts/PDF/U4E00.pdf)：PDF2ページ、印刷ページ558、U+4E00のJ0-306C。SHA-256 `9c2527a34623870413a348778a7804475c15e92960017dd3693ba18fd121aaf9`。
- 固定snapshotの `u4e00@46` は `u4e00-j@30` を参照。依存先の原KAGEは `1:0:0:14:101:186:101`。参照変換は全体を同じ200×200領域に置く恒等変換。
- KAGEは `@kurgm/kage-engine@0.7.0`、`kUseCurve=false` で描画。2ポリゴンが出ますが、右端のうろこのポリゴンを独立した筆画とは数えていません。

ページ全体を150dpi、J0-306Cの字形と典拠ラベルを600dpiで確認し、KAGEの全字形を描画して比較しました。原KAGEの確認は画像の観察を補強する証拠であり、有限座標の描画成功だけで判定したものではありません。

## 四つの観察

| 比較項目 | 観察と判断 |
| --- | --- |
| 部品 | 両方とも横画一つだけで、追加部品や点はない |
| 配置 | 両方とも中央付近を横に渡る一本の画。囲みや複数部品の相対配置はない |
| 筆画構造 | 連続した一本の画、両端の二端点。交差、分岐、閉領域はない |
| 地域字形 | 比較したJ0-306Cと候補の全体に、横画一つという構造以外の地域的構造差は見られない |

線幅、端部、輪郭の細部や比率は同一ではありません。判定基準は[判断記録の契約](REVIEW-DECISIONS.md)で定義した構造の比較であり、輪郭・ピクセル一致ではありません。他地域、同じ名前の別版、U+4E00の多数の別候補への一般化はしません。人間の独立レビューを受けたという記録でもありません。

## 記録と再現

[判断記録](one-review-decision.jsonl)に四項目の観察、基準、判断者、日時、原資料位置、画像・原KAGE・SVGのハッシュ、限界を保存しています。[検証結果](one-review-validation.json)で配布DBの候補版と結び付くことを確認しました。[KAGE由来SVG](review-artifacts/u4e00-46.svg)も公開し、再生成したハッシュが一致しました。GlyphWikiデータの条件は [NOTICE](../NOTICE.md) と [元ライセンス](../licenses/GLYPHWIKI.txt)を参照してください。

```powershell
python tools/prepare_decision_bundles.py docs/one-review-decision.jsonl --dataset path/to/kanji-kage-map-v0.1.sqlite3 --output one-bundles.json
node tools/render_bundles.mjs one-bundles.json one-rendered.json
python -m kanji_kage_map lookup U+4E00 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --glyph u4e00 --review-decisions docs/one-review-decision.jsonl --output one-reviewed.json
```

典拠PDFの確認用画像はローカルのみで、PDF・画像・埋め込みフォントを再配布しません。ローカルのクロップ再現は以下の通りです。

```powershell
pdftoppm -f 2 -l 2 -singlefile -r 150 -png path/to/U4E00.pdf page-2
pdftoppm -f 2 -l 2 -singlefile -r 600 -x 1600 -y 760 -W 300 -H 300 -png path/to/U4E00.pdf one-j-source
```

## 件数の扱い

独立した判断記録には、今回初めて構造一致の判断が1件入りました。初回配布DBとそのcoverage.jsonは不変で、同版の確認済み件数は引き続き0件です。検索結果にはこの判断を添付しますが、元mappingのreview_statusやselected_glyphを自動変更しません。判断の共通スキーマ化・配布DB・集計への統合と、残りの字形レビューは未完了です。
