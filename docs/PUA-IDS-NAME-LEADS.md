# 全PUAの既存IDS形式名による追加調査

2026-11-04。E87Dで得られた探索の手掛かりを、採用版のPUA全6,030件に適用した。固定IDS_PUA.TXTの構造記述から名前の検索文字列を作り、固定GlyphWiki dump内にその名前が実在する場合だけ調査候補とした。KAGEの生成・合成・補正は行っていない。命名規則の一般的な保証ではなく、このスナップショット内で実在を確認した結果である。

| 区分 | 件数 |
| --- | ---: |
| 調査対象PUA | 6,030 |
| 既存名の調査候補あり | 4,925 |
| 検索できたが該当名なし | 854 |
| この規則では検索しない記述 | 251 |
| 候補リンク | 4,927 |
| 重複を除く字形名・版 | 4,925 |
| preview.2では候補なしだった識別子のうち今回候補を得たもの | 3,165 |

4,927リンクは、preview.2の当該識別子にある候補の名前・版とはいずれも異なる。同じ字形の別名参照である可能性は残り、「新しい独立字形が4,927個」という意味ではない。元の候補に自動追加せず、[調査台帳](pua-ids-name-leads.jsonl.gz)に分離して保持する。字形一致の確認済み件数や既存公開DBの候補率は変更しない。

## 探索と保留

構造演算子と、固定台帳で割当済みとされたUnicodeの葉だけから成る、引数数の正しい式を対象にした。各文字を `uXXXX` 形式にし、ハイフンでつないだ名前を完全一致検索する。例は `⿰飠盧` → 検索名 `u2ff0-u98e0-u76e7`。この文字列から図形やKAGEを作る処理はない。

PUAの葉を提供元を無視した名前へ変換しない。番号部品、未知記号、修飾記法、不正な引数数などは理由を残して保留する。`or` で明示された選択肢は個別に検索する。接尾辞付きの別名や間接参照全体は今回の規則の対象外。全6,030件の行を保持し、保留行も省かない。[探索集計](pua-ids-name-leads-summary.json)

## 依存と描画

全4,925字形を指定版で取り出し、原KAGEとすべての依存参照を取得した。依存問題は0件。既存の固定エンジン `@kurgm/kage-engine@0.7.0` で全件が有限・非空の描画を返した。[描画台帳](pua-ids-name-rendering.jsonl.gz)に、対象識別子・字形名と版・SVGハッシュ・輪郭数を保存した。原典字形と全件目視比較したとは主張しない。

比較元は公開済みpreview.2の実取得DBで、SHA-256を検証してから比較する。[比較・検証集計](pua-ids-name-review-summary.json)。構造式の誤読やPUAの同一視を防ぐ3テストを追加し、全82テストが成功した。初回の全テスト実行ではWindowsの既定一時フォルダーへの権限エラーが起きたため、作業領域内の一時フォルダーで再実行した。

## 再生成

固定原本・索引とレビュー用Node依存を準備し、公開preview.2のDBを指定する。

```text
python tools/research_pua_ids_names.py --output data/generated/pua-ids-name-research
python tools/prepare_pua_ids_name_review.py --leads data/generated/pua-ids-name-research/pua-ids-name-leads.jsonl.gz --summary data/generated/pua-ids-name-research/pua-ids-name-leads-summary.json --published .cache/corrected-published/offline/dataset.sqlite3 --output data/generated/pua-ids-name-research/review
node tools/render_bundles.mjs data/generated/pua-ids-name-research/review/bundles.json data/generated/pua-ids-name-research/review/rendered.json
```

`bundles.json`には指定版の原KAGEと依存閉包が入る。描画結果を対応確定へ昇格させない。残る作業は典拠・版の照合、原典やフォントとの構造比較、差異・判断根拠の記録、および検索用補足データの配布形式への統合である。
