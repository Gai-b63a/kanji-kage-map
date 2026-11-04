# 出典ID訂正後の全件再生成

2026-11-04。固定原本から再抽出したPUA候補を依存監査に再投入し、全109,556件の対応表を別ディレクトリへ再生成した。公開済み `v0.1.0-preview.1` および `v0.1.0-review.1` の配布物は変更していない。これは次版の準備記録で、訂正版の公開完了を示さない。

## 全項目比較

実ダウンロード済み初回公開DB（SHA-256 `99d876fce6118a3b80924fd05b3b9c8580ac0496a5db403daba0ac6ff64b3ab6`）と、再生成JSONLを全ID・全JSONフィールドについて比較した。候補内の根拠も比較対象とし、配列の順序も区別した。重複・追加・欠落IDとsnapshot不一致は失敗させる。

- 109,555件は全項目一致。
- `babelstone:han-pua:1.473:U+EADD` のみ、`source_refs` が空配列から `USAT05567` を含む配列へ変わった。
- 同じ行の探索状態が `requires_source_evidence` から `no_candidate_in_searched_rules` へ変わった。出典IDは認識したが、探索範囲内に対応候補がない。
- 候補あり105,657件、候補リンク955,185件、依存問題のある候補リンク7件は不変。一致判断・候補選択の追加はない。

正本の差分は [mapping-regeneration-change.json](mapping-regeneration-change.json)。再生成JSONLのSHA-256は `ecf47b9cb361af7fb447f08000d34e811391fc6a869f7c9872463597e6daf6e1`。

## 依存監査

訂正PUA候補ファイルのSHA-256 `003041667be119b1a0a59cec7e6a5b7c1663f5fe0bebd2ee724ed85dd533a8cf` を入力として監査を再実行した。2,410候補リンク、2,406根、8,278依存ノード、10,149辺について、原KAGE・辺・局所問題・候補別依存状態の4成果物は旧監査とバイト単位で一致した。監査要約の変更は入力候補ハッシュのみ。

[corrected-dependency-verification.json](corrected-dependency-verification.json) に新旧ハッシュと訂正後の監査要約を保存した。この検査は字形一致の認定ではない。

## 再実行

独立した `data/generated/corrected-release/` に既存の `inventory.jsonl`、Unicode候補 `candidates.jsonl`、Unicode側 `dependency-audit/` をコピーする。`pua-research/pua-candidates.jsonl` には訂正後のPUA探索結果を置く。旧入力を上書きしない。

```powershell
python -m kanji_kage_map audit-dependencies --candidates data/generated/corrected-release/pua-research/pua-candidates.jsonl --output data/generated/corrected-release/pua-research/dependency-audit
python -m kanji_kage_map assemble --directory data/generated/corrected-release --output data/generated/corrected-release/mappings.jsonl
python tools/audit_mapping_regeneration.py .cache/published-preview/offline/kanji-kage-map-v0.1.sqlite3 data/generated/corrected-release/mappings.jsonl --output docs/mapping-regeneration-change.json
python -m kanji_kage_map build-release --directory data/generated/corrected-release --output dist/kanji-kage-map-corrected.sqlite3
```

比較処理の回帰テストは、入れ子の候補根拠の変更、未存在キーとnullの差、重複・追加・欠落ID、snapshot違いを検査する。全66テスト通過。

配布DBも生成済み。全5テーブルを公開版と比較し、対応表の上記1件2項目以外は一致した。metadataの変更は対応表入力ハッシュのみ。原KAGE 1,201,970件、依存辺1,810,938件、問題4件を保持する。[生成記録](corrected-portable-build.json)と[全テーブル検証](corrected-portable-verification.json)を保存した。

次版の公開には、レビュー履歴同梱、梱包、公開後の実取得確認が引き続き必要。

## 配布準備の進捗

レビュー履歴同梱とローカルZIP生成は完了。全165収録ファイルのハッシュ、同梱前後の全5テーブル一致、展開したパッケージだけによるEADD・「一」・「海」の検索を確認した。全71テスト通過。

GitHubの[再生成ジョブ](https://github.com/Gai-b63a/kanji-kage-map/actions/runs/41811694731)は、固定原本の再取得を完了し、台帳・索引の再構築へ進んだ。実行対象は `1d5f5cff3172eb0d7083155d9c0e8bfcc77084cf`。ジョブ開始を公開成功とは扱わない。

公開後は全添付とRelease API応答を新しいディレクトリへ実取得し、以下を実行する。`--base` はローカルで全件比較済みの訂正後・レビュー同梱前DB、`--original` は実取得した初回公開DB。物理DBハッシュは環境差を許容するが、原レコード全件とmetadataを比較する。

```text
python tools/verify_review_release_download.py .cache/corrected-published --tag v0.1.0-preview.2 --base dist/kanji-kage-map-corrected.sqlite3 --original .cache/published-preview/offline/kanji-kage-map-v0.1.sqlite3 --output docs/corrected-release-download-verification.json
```

この検証はAPIの添付サイズ・ハッシュ、外部SHA256SUMS、ZIP内の全ハッシュ、ZIPと単独添付の同一性、解凍DBハッシュ、全レコード比較、埋込レビューのハッシュと候補への適用条件を検査する。強化後の検証処理を、既に実取得済みのreview.1全6添付・152収録ファイル・全DBレコードで再実行し、成功を確認した。訂正版の実取得検証は未実施。
