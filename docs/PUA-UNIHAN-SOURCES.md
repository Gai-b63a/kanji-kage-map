# PUA出典IDとUnicode IRG典拠の照合

2026-11-04。Unicode 18.0.0の公式Unihanを取得し、採用PUA表1.473のSource Refs列から抽出した出典IDと、11種類の `kIRG_*Source` プロパティの値を文字列の完全一致で照合しました。[UAX #38 第41版](https://www.unicode.org/reports/tr38/tr38-41.html)がこれらのプロパティをIRG典拠情報として定義しています。

## 結果

| PUA識別子の状態 | 件数 |
| --- | ---: |
| 一つのUnicode識別子に出典IDが一致 | 1,297 |
| 出典IDはあるが今回の完全一致なし | 1,889 |
| 比較する出典IDなし | 2,844 |
| 合計 | 6,030 |

一致イベントは1,376件、重複排除したUnicode側の文字は1,292件です。一つのPUA行に複数の出典IDがあったり、異なるPUA行が同じUnicode文字を指したりするため、これらの母数は異なります。複数Unicode文字を指すPUA行は今回0件でしたが、処理はその場合も候補を消さず保持します。

1,297件のうち103件は従来のGlyphWiki出典ID完全一致名検索で候補がなかったPUAです。Unicode文字を経由して、既存データセットの候補を調べる手掛かりが得られました。

| PUA 1.473 | 原表の出典ID | UnihanのUnicode文字 | 収録済み候補の例 |
| --- | --- | --- | --- |
| U+E0C7 | UK-20674 | U+32580 | u32580@3 |
| U+E0CC | UK-20691 | U+325F4 | u325f4@3 |
| U+E0CD | UK-20688 | U+325D4 | u325d4@3 |
| U+E080 | UK-20656 | U+333E5 | u333e5@4 |

最初の3件は従来のPUA検索で候補なしでした。E080には既に出典ID名候補があり、今回Unicode側の対応手掛かりを追加しました。表のKAGE名と版は固定配布DBで確認した例であり、PUAに対する新しい確定対応ではありません。

## 証拠と限界

- [全6,030行の照合結果（JSONL gzip）](pua-unihan-source-matches.jsonl.gz)
- [入力版・原本ハッシュ・集計](pua-unihan-summary.json)
- [取得ロック](../review-unihan.lock.json)

各行にPUA表の行位置、Unihanのプロパティ名・行番号・生の値を記録しました。Unicode側の対象が採用版の台帳に存在することも確認しています。ASCIIの大文字小文字、区切り記号、接頭辞を変換していません。例えば `USAT05567` を `SAT-05567` と見なす処理はありません。非一致は今回の11プロパティと表記での非一致に限り、符号化されていないという判断ではありません。

**出典ID一致は字形一致ではありません。** PUA表の誤記、典拠の版差、地域差、部品と完成字形の違いは別途調査が必要です。採用表とフォントの版不一致も未解決です。既存DBの候補配列・レビュー状態・選択字形は変更しておらず、確認済み字形一致は0件のままです。前回の[調査一覧](PUA-REVIEW-QUEUE.md)は出典ID名だけによる探索状態を記録したもので、この追加の照合結果とは検索範囲が異なります。

## 再現と利用

```powershell
python -m kanji_kage_map restore --lock review-unihan.lock.json
python tools/review_pua_unihan.py
python -m kanji_kage_map lookup U+32580 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --glyph u32580 --output e0c7-unicode-lead.json
```

最後のコマンドはUnicode U+32580の候補データを取得します。PUA E0C7として確定したデータではありません。生成には先に[PUA出典抽出修正](PUA-DISCOVERY-CORRECTION.md)の再生成手順を実行してください。

再生成結果の圧縮バイト一致、6,030行のID一意性、全Unicode対象の台帳所属を検証しました。原アーカイブとメンバーのSHA-256を別々に保存しています。Unihan由来データは© 2026 Unicode, Inc.、[Unicode License v3](../licenses/UNICODE.txt)の対象です。[Unicode利用条件](https://www.unicode.org/copyright.html)にあるデータファイルの区分を確認しました。原フォントやUnicodeコード表画像はこの照合結果に含みません。
