# 根拠と訂正履歴を持つレビュー判断

`glyph-review-decision-v1` は既存の候補対応表とは別に保存するJSONL判断記録です。検証コードは `kanji_kage_map/review_decisions.py`。既存の共有mappingスキーマやサイトの入力形式は変更していません。判断の取り込み・選択・集計を既存の配布DBへ統合する工程は今後必要です。

## 判断の範囲

| 範囲 | 許される判断 |
| --- | --- |
| `whole_glyph` | equivalent、different、inconclusive、withdrawn |
| `feature` | feature_agreement、feature_difference、inconclusive、withdrawn |

`whole_glyph` の判定基準 `structural_glyph_v1` は、指定された典拠字形に対する部品、配置、筆画の接続・分岐関係、地域字形の構造を比較するものです。書体の太さ・うろこ・曲線の細部まで同じ輪郭であるという意味ではありません。部品の有無や筆画のつながりを単なる書体差として除外しません。

`equivalent` には、`components`、`layout`、`stroke_topology`、`regional_form` のすべてを比較し、すべて一致という観察を記録する必要があります。対象資料の版対応も確認済みである必要があります。一特徴だけの一致、未確認項目、版不一致を持つ記録では受理しません。検証は判断記録の整合性を確認するもので、その内容が真であることを自動証明するものではありません。

`different` は、指定した典拠との構造的一致を否定する具体的な差を少なくとも一つ要します。他の典拠や地域にも一致しないという全称的な判定ではありません。版対応が未確認なら全体の一致・不一致判定にはせず、`inconclusive` として不足を記録します。`feature` の結果から全体の一致へ昇格できません。

## 必須記録

- 一意な `review_id`、版付き対象識別子、GlyphWiki snapshotと `name@revision`。
- 比較範囲、基準、典拠ID。典拠の提供元・版・URL・原本ハッシュ・ページ等の位置・版対応状態。
- 判断者の名前と人間／AIの区別、タイムゾーン付き日時。
- 比較証拠の種類・ハッシュ・位置、観察項目と一致／差異／未確認、限界、判断理由。
- 訂正する場合の `supersedes`。初回はnull。

未知の項目、欠けた項目、版のないKAGE参照、判断と観察の矛盾などを拒否します。識別子の存在や対象KAGE版への結び付きは配布DBと照合します。証拠ファイルの署名検証、証拠画像の自動目視、判断者の本人確認は行いません。

## 訂正と撤回

以前の行を上書きせず、新しいIDの行を追記します。同じ対象・snapshot・KAGE版・比較範囲・典拠版／ハッシュ／位置を対象とする場合、直前の有効記録を `supersedes` で明示します。過去の分岐点から別の訂正を黙って採用したり、別典拠の判断を置換したりできません。

撤回は `withdrawn` の新しい行で行います。履歴にも有効記録一覧にも撤回行を残します。候補を自動採用する処理はないため、撤回が「一致」に読み替わることはありません。同じ文字でも別地域・別候補の判断は共存します。

## 実際の記録：海

[2件の判断記録](sea-review-decisions.jsonl)は[既存の特徴観察](unicode-sea-review.json)に基づく判断です。新たな全体の画像比較を実施したという記録ではありません。

- `u6d77@19` とG0-3A23：内側の縦線と二点という記録済みの構造差を根拠に、その中国典拠に対する `structural_glyph_v1` では `different`。
- 同じKAGEとJ0-3324：内側筆画一特徴の一致だけでは全体を確認できないため `inconclusive`。

判定の典拠・範囲を外して「海は不一致」「日本字形は確認済み」と解釈してはいけません。採用済み字形は設定しておらず、字形一致確認済み件数は0件のままです。

## 検索と検証

```powershell
python -m kanji_kage_map lookup U+6D77 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --glyph u6d77 --review-decisions docs/sea-review-decisions.jsonl --output sea-decisions.json
python tools/validate_reviews.py docs/sea-review-decisions.jsonl --dataset path/to/kanji-kage-map-v0.1.sqlite3 --output reviews-validation.json
```

結果の `review_decisions` に該当する履歴と有効IDを添付します。既存mappingの `review_status` や `selected_glyph` を上書きしません。検証器は記録全体の履歴を検査した後、対象識別子のsnapshot・候補版を照合します。`--glyph` 指定時はその候補の記録に絞ります。

[全記録検証結果](sea-review-decisions-validation.json)は2件・1識別子について配布DBとの結び付きを確認したものです。一般的な受理・棄却・撤回はfixtureテストで検証していますが、別途[「一」の日本典拠に対する構造比較](UNICODE-ONE-REVIEW.md)で、実データの `equivalent` 判断を1件記録しました。このコマンドには最新コードが必要で、初回配布ZIPには含まれません。
