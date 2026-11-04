# レビュー履歴を同梱する独立DB

初回公開DBを変更せず、検証済みレビュー履歴を加えた別のSQLiteを生成できます。最新の検索コードは同梱履歴を自動取得します。追加の `--review-decisions` 指定や元JSONLの携帯は不要です。

```powershell
python tools/include_reviews.py path/to/kanji-kage-map-v0.1.sqlite3 docs/sea-review-decisions.jsonl docs/one-review-decision.jsonl --output dist/kanji-kage-map-reviewed.sqlite3 --report reviewed-build.json
python -m kanji_kage_map lookup U+4E00 --dataset dist/kanji-kage-map-reviewed.sqlite3 --glyph u4e00 --output one-reviewed.json
```

入力DBには読み取り専用で接続し、SQLiteのbackup APIで新しいDBへコピーします。出力が既に存在すれば拒否します。判断の形式・履歴・対象ID・snapshot・候補版を検証してからコピーし、一時DBの整合性と検索での読み戻しを確認して完成名へ移します。

## 保存内容と互換性

既存の5データテーブルと元メタデータをそのまま保持し、metadataへ次の5キーを追加します。

- `review_ledger_jsonl`：訂正・撤回も含む完全な判断履歴。
- `review_ledger_sha256`：埋め込んだUTF-8 JSONLのハッシュ。
- `review_parent_dataset_sha256`：元DBの物理ハッシュ。
- `review_ledger_inputs`：追加入力のパスとハッシュ。
- `review_application`：範囲付き判断の添付であり、自動選択しないことを示す値。

既存portable-v0.1形式のテーブル・レコードを変更しない追加です。古い検索コードはこのメタデータを解釈しないため、レビューの表示には最新コードが必要です。古いコードでもレビューを表示できるという互換性は主張しません。

`review_decisions.history` と `active_review_ids` が検索結果に付きます。対象のレビューがなければ空配列です。元mappingの `selected_glyph`、候補配列、`review_status` はそのままです。これは根拠のない自動選択を避け、地域・判定基準・典拠を持つ判断を失わず取得するためです。全体のcoverageに判断を集計する機能は別途必要です。

## 追記・撤回

レビューを含むDBを次の生成の入力にすると、既存履歴を継承して新しいJSONLを追記します。重複ID、既存対象へのsupersedesなしの書き込み、古い判断からの分岐、版違いを拒否します。撤回も既存行を消さず履歴に残します。

埋め込み済みDBに `lookup --review-decisions` で別履歴を被せることは拒否します。上書きの代わりに、この生成処理で明示的に追記した別DBを使ってください。候補取得・bundle再描画用の検証ツールは、同梱済みDBでも使えます。

## 実データ検証

初回公開DBから生成したローカル成果物には、構造一致1件、特定典拠との差異1件、全体比較の証拠不足1件を同梱しました。[生成記録](reviewed-portable-build.json)

[全レコード比較](reviewed-portable-verification.json)では次の値がすべて元DBと一致しました。

| テーブル | 比較行数 |
| --- | ---: |
| inventory | 109,556 |
| mappings | 109,556 |
| glyphs | 1,201,970 |
| dependencies | 1,810,938 |
| issues | 4 |

元メタデータの値も全件一致し、上記5キーだけが追加されました。「一」は1判断、「海」は2判断、「龍」は0判断として検索できました。fixtureでは追記撤回後に旧判断が有効扱いされないこと、元DB不変、既存出力拒否、候補版違い拒否を確認しています。

このDBファイルは現在ローカル生成・検証済みで、GitHub Releaseへの添付はまだ行っていません。生成コードと記録を公開し、次の固定配布版へ組み込む準備段階です。初回ReleaseのDBやチェックサムを置き換えたという意味ではありません。
