# PUA出典IDの区切りなし表記を保持する修正

2026-11-04。採用した[BabelStone Han PUA表](https://www.babelstone.co.uk/Fonts/PUA.html)1.473版の全6,030行について、出典欄が空でないのに出典IDを抽出できない行を調べました。初回配布版の抽出規則では、U+EADDの `USAT05567`（固定HTMLの21253行目）1件が該当しました。原表のSHA-256は `a31b6fa8b39f2258dcb64008971936a524bdc462f3b753b3e73d24fbbcec2417` です。

従来の規則はハイフンまたはアンダースコアのある識別子を対象としていました。今回、原表にある `USAT` + 5桁の数字をそのまま保持する規則を追加しました。`USAT-05567` への表記変更や、別出典との同一視はしていません。固定dumpの完全一致名 `usat05567` は見つからず、候補は増えません。

| 項目 | 初回配布版 | 修正後の再生成 |
| --- | --- | --- |
| U+EADDの出典ID | 空配列 | USAT05567 |
| U+EADDの調査状態 | requires_source_evidence | no_candidate_in_searched_rules |
| BabelStone候補あり識別子 | 2,252 | 2,252 |
| 出典ID名の検索で候補なし | 933 | 934 |
| 出典根拠の調査が必要 | 2,966 | 2,965 |

最後の行はPUAと番号付き部品を合わせた件数です。修正後はPUA 2,844件と番号付き部品121件になります。出典欄が空でないPUA行は3,186件で、修正後はすべての行から少なくとも一つのIDを抽出できました。これは各欄の全内容を完全に解析したという証明ではありません。

公開DBを基準に全BabelStone 6,151識別子の出典ID、調査・対応・レビュー状態、選択、候補名と版を照合し、この1件だけが変わることを確認しました。[差分監査](pua-discovery-change.json)に入力ハッシュと変更前後の値を保存しています。候補リンク数、字形一致確認数、全109,556識別子の母集団は変わりません。

## 配布版との関係

`v0.1.0-preview.1` の配布DBとチェックサムは変更していません。この修正は最新コードでの再生成に反映され、既存配布DBでU+EADDを検索すると旧状態を返します。新しい配布版に更新するまでは、本記録を初回配布版の訂正として扱ってください。既存版の再現にはタグのコードを用います。

## 再現

固定入力を復元・索引化した後、修正結果を別ディレクトリに生成します。

```powershell
python -m kanji_kage_map pua-candidates --database data/generated/glyphwiki.sqlite3 --source-rows data/generated/source-rows.jsonl --inventory data/generated/inventory.jsonl --output data/generated/pua-source-id-fix
python tools/audit_pua_discovery_change.py .cache/published-preview/offline/kanji-kage-map-v0.1.sqlite3 data/generated/pua-source-id-fix/pua-candidates.jsonl data/generated/source-rows.jsonl
```

DBのパスは初回配布版を展開した場所に置き換えてください。元表の出典表記が正しいか、別表記の典拠に対応するか、候補字形が存在するかは次の調査事項です。現時点では字形一致やUnicodeへの移行先を推定していません。
