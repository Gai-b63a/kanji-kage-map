# E87Dの既存KAGE調査候補

2026-11-04。固定PUA表1.473のE87D行は `⿰飠盧` と《潛確居類書》卷96・25bへのリンクを持つ。これを探索の手掛かりとして、固定GlyphWiki索引のlatest全2,095,944行から、原KAGE文字列に `u98e0` と `u76e7` の両方を含む行を抽出した。既存のKAGEを取り出しており、IDSからKAGEを生成していない。

| 調査候補 | 固定dump内の内容 | 描画 |
| --- | --- | --- |
| `ka-kc04555@2` | `u2ff0-u98e0-u76e7` への別名参照 | 下段の候補とSVGハッシュ一致 |
| `takata_my-gaiji-0099@1` | `u98e0-01@1` と `u76e7-g@2` を参照 | 別のSVGハッシュ |
| `u2ff0-u98e0-u76e7@2` | `u98e0-01` と `u76e7-j` を参照 | 版なし参照は固定dumpのlatestへ解決 |

3件とも依存閉包を取得でき、問題なし。固定エンジン `@kurgm/kage-engine@0.7.0` で各53輪郭の有限・非空出力を得た。候補画像も目視確認した。3件は独立した3字形ではなく、うち2件は今回の条件で同じ描画になる。これを原典字形との一致や同じ典拠を持つことの証明には使わない。

[調査結果](pua-e87d-candidate-leads.json)に探索式、検索対象件数、各字形の版・関連字・元行番号・原KAGEハッシュ・依存先を含むbundleを保存した。[描画記録](pua-e87d-candidate-rendering.json)にはエンジン、SVGハッシュ、輪郭数を保存した。KAGEのライセンスは [NOTICE](../NOTICE.md) と [GlyphWikiライセンス](../licenses/GLYPHWIKI.txt) を参照。

## 再実行

固定原本と索引、既存のレビュー用Node依存を準備した環境で実行する。

```text
python tools/research_e87d_candidates.py --output docs/pua-e87d-candidate-leads.json --bundles data/generated/review/e87d-bundles.json
node tools/render_bundles.mjs data/generated/review/e87d-bundles.json data/generated/review/e87d-rendered.json
```

探索は部品名トークンの文字列検索である。別名、別の部品名、さらに間接的な依存経路を網羅するものではない。PUA表ハッシュとGlyphWikiスナップショットを検査し、不一致なら停止する。各bundleの原データは検索結果と再照合する。

## 未確定事項

[原典画像の観察](pua-e87d-source-image.json)に記録した巻・丁番号と対象字の同定、版の一致、各KAGE候補との構造比較が残る。今回の記録は探索候補であり、字形一致判断ではない。公開済みDBのE87Dは候補0件・`requires_source_evidence`のまま保持し、この調査用補足に3件を分離して保存する。候補率の分子へは加算していない。
