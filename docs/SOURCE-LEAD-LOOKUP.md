# 版付きPUAから典拠・Unicode候補・KAGEを取得する

最新コードの `lookup-source-leads` は、[Unihan典拠照合](PUA-UNIHAN-SOURCES.md)を使い、版付きPUAからUnicode側の候補を取得します。既存の公開DBと照合結果の2ファイルだけで動作し、巨大な上流dump索引や原Unihanアーカイブの再取得は不要です。

## 候補を調べる

```powershell
python -m kanji_kage_map lookup-source-leads babelstone:han-pua:1.473:U+E0C7 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --output e0c7-leads.json
```

結果には次の情報が入ります。

- `pua_mapping`：配布DBの元のPUA対応レコード。E0C7の従来候補は空配列のままです。
- `source_relation`：出典ID `UK-20674`、PUA表の位置、Unihanの行・プロパティ、Unicode U+32580への手掛かり。
- `unicode_leads`：Unicode側の候補名・固定版・取得根拠・依存監査状態。
- `provenance`：照合ファイルと集計のハッシュ、両典拠の版・URL・原本ハッシュ。

## 特定候補のKAGEを取得する

```powershell
python -m kanji_kage_map lookup-source-leads babelstone:han-pua:1.473:U+E0C7 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --unicode-target U+32580 --glyph u32580 --output e0c7-kage-lead.json
```

`unicode_leads` のU+32580に `u32580@3` の原KAGE、依存辺、依存字形、問題一覧、静的構文検査が入ります。対象を指定していないUnicode候補にはbundleを付けません。

これは**Unicode側候補の調査用取得**です。PUAの確認済み対応への昇格や、選択字形の設定はしません。地域字形、典拠の版差、PUA見本と候補の違いを別途確認する必要があります。出典IDがない場合や一致がない場合もPUAレコードは取得でき、`unicode_leads` は空配列です。

`--glyph` を使う際には `--unicode-target` が必須です。典拠にないUnicode対象や候補にない字形を指定すると拒否します。PUAは提供元と版を含める必要があり、`U+E0C7` だけの指定では検索しません。

## 整合性と配布版

照合結果のチェックサム、全PUAの集合、台帳ハッシュ、PUA原典ハッシュ、Unicodeの版、典拠IDとプロパティを検査します。集計とデータのハッシュ照合は署名による真正性の保証ではありません。信頼するリポジトリの固定コミットから取得してください。

既定では `docs/pua-unihan-source-matches.jsonl.gz` と `docs/pua-unihan-summary.json` を読みます。別の場所にある場合は `--matches` と `--summary` で指定できます。初回配布版ZIPにはこの追加コマンドがないため、コードは最新リポジトリを使ってください。配布DBは初回版のまま利用できます。

元PUAレコードと追加照合の探索規則は別です。U+EADDの抽出訂正など、最新照合に含まれて配布DBには未反映の情報は `source_relation` 側に残し、`pua_mapping` を上書きしません。

## 全件検証

```powershell
python tools/audit_source_leads.py path/to/kanji-kage-map-v0.1.sqlite3
```

[全件検証記録](source-lead-lookup-audit.json)は、PUA全6,030件の検索と、従来候補のなかった103件から到達するUnicode候補のbundle取得を検査します。描画や字形一致の検査ではありません。既にPUA候補があった項目についてはUnicode側の候補一覧取得までが今回の検証範囲です。
