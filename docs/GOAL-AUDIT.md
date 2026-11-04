# 目標全体の達成状況監査

2026-11-04。目標は完了していません。初回の候補データ公開を、全件の字形対応・レビュー完了へ読み替えません。以下は現在のコード、スキーマ、生成記録、配布物に照らした監査です。古い文書の「次の作業」「未公開」は、その文書の作成時点の記述として区別します。

| 要件 | 確認した証拠 | 判定・不足 |
| --- | --- | --- |
| 原本URL・版・日時・サイズ・ハッシュ固定、未取得を偽装しない | sources.lock.json、glyphwiki.lock.json、review-*.lock.json、取得・復元コード | 採用原本は取得済み。PUAフォントの実版不一致は明示。上流が変われば旧版復元は失敗し得る |
| 全Unicode漢字・部品、版付きPUA・番号部品を保持 | inventory-summary.json、portable-verification.json、inventory.py | 109,556件を保持。台帳と対応表のID集合一致を全件検証済み |
| IDSの葉・未知部品・空欄・原行を保存、集合差を明示 | INVENTORY-AUDIT.md、inventory-source-review.json、公開JSONL | 380,334出現、Unicodeのみ5,319件、空欄PUA163件を保持。160解析イベントを61IDで原資料照合済み。意味的な正しさの全件確認ではない |
| 公式dumpの版固定、原KAGE・関連字・資料行の保存 | glyphwiki-index-summary.json、glyphwiki.py、公開glyphs JSONL | 最新2,095,944／履歴6,622,499行を索引化。解析除外を黙認しない。取得した原KAGEを変更しない |
| 全IDの候補状態、探索根拠、候補なしも保持 | mappings-summary.json、mappings.schema.json、公開DB | 初回版955,185候補リンク。Unicode名・接尾辞・関連字・出典IDの探索範囲を明示。他の命名体系を網羅したとは主張しない |
| 指定版と無版参照を区別、閉包・循環・欠落・上限を検査 | audit.py、glyphwiki.py、test_audit.py、test_glyphwiki.py、dependency-summary.json | 全候補閉包を監査。4局所所見が7候補へ影響。欠落参照1件を保持。原KAGEと参照辺を取得可能 |
| 全KAGEの静的検査と候補への影響把握 | syntax-summary.json、audit_syntax_impact.py、syntax-impact-summary.json | 全1,201,970字形を直接検査し、さらに955,185候補リンクへ伝播。幾何学・命令全組合せ・字形一致までは検証しない |
| PUAの提供元・版分離、例外の根拠と次の調査事項 | pua.py、PUA-REVIEW-QUEUE.md、NUMBERED-COMPONENTS.md | 全6,151件に調査事項あり。番号部品の参照先PUA版、孤立／変形部品の対応は未確定 |
| 符号化移行先と典拠の調査 | PUA-UNIHAN-SOURCES.md、SOURCE-LEAD-LOOKUP.md | 1,297件にUnicode典拠ID一致。103件から107の新しい候補bundleを取得検証。これをPUA字形一致には昇格しない |
| 目視比較、地域差・複数候補・近似のレビュー | UNICODE-SEA-REVIEW.md、FONT-REVIEW.md、diagnostic-review.json | [「一」](UNICODE-ONE-REVIEW.md)の一候補版・日本典拠について構造一致判断1件を独立記録。その他は限定的な特徴比較と診断。全件レビューは未完了で、初回配布DBの確認済み件数は0件のまま |
| 根拠・差・判断者・日時を持つ確定判断の契約 | feature_reviews.py、unicode-sea-review.json、schemas/mappings.schema.json | 独立した[判断記録](REVIEW-DECISIONS.md)の契約・検証・訂正／撤回履歴・検索添付を実装。既存mappingスキーマはunreviewedのみで、[別DBへの履歴同梱](REVIEWED-PORTABLE.md)も実装・全レコード比較済み。[レビュー補足版の公開・実取得検証](REVIEW-PUBLICATION.md)も完了。集計と共有スキーマ化は未完了 |
| 手動対応を根拠付きで保存 | PLAN.mdのoverrides.jsonl要件 | 手動確定対応はまだない。overrides.jsonlの生成・検証・適用経路は未実装。空ファイルを置くだけで達成とはしない |
| 分母別候補率・確認済み率・依存率 | coverage.json、coverage.py、test_coverage.py | 初回公開版の母集団ごとに算出済み。後続の出典照合を既存候補率に無条件加算しない |
| 原本・フォント・エンジン・コードの権利区分 | NOTICE.md、LICENSE、licenses/、配布ZIPの内容 | 配布範囲を識別子・典拠事実・KAGE等に限定。原PUA表本文・フォント・画像の再配布許諾を推定しない |
| JSONL正本、独立SQLite、オフライン検索 | release.py、package_release.py、PUBLICATION.md | 初回版は別環境で再生成し、全レコード一致と公開9添付の取得・ハッシュを検証済み |
| 最新の修正・追加レビューを一つの固定配布版へ統合 | PUA-DISCOVERY-CORRECTION.md、最新main、初回Release | 一部完了。レビュー補足版には最新検索・補助資料・判断を同梱し公開検証済み。基礎mapping行を変更する訂正再生成版は未完了。初回版は不変 |

## 残る実作業の優先順位

1. **判断記録の統合**：独立した判断契約と履歴検証を実装した。独立DBへの履歴同梱と自動取得も実装した。文脈を保った集計、曖昧な複数判断の扱い、共通スキーマ化を進める。候補選択操作を判断へ昇格させない。共有スキーマの変更は担当境界を調整してから行う。
2. **典拠と字形のレビュー**：PUA表／フォントの版継続性、番号部品の対象版、地域差、同一Unicodeへの複数PUA行、複数KAGE候補を優先する。必要な原資料が見つからない場合は具体的な不足を残す。全件確認済みの主張には対象範囲に相応する証拠が必要。
3. **監査所見の判断**：静的検査の所見は意図的な用法の場合もある。影響する候補を取得し、エンジンの実挙動・原資料・字形との関係を調べる。未対応命令や数値を推測して書き換えない。
4. **次の固定配布版**：[訂正後の対応表・配布DB再生成と全件比較](CORRECTED-REGENERATION.md)は完了。変更はEADDの出典IDと探索状態だけ。レビュー履歴同梱、梱包、公開後の実ダウンロード検証を続ける。追加した補助記録を初回版に同梱済みと説明しない。

未解決を明示したリリースは目標に含まれる許容事項です。ただし、未実装の判断契約や未完了のレビューを「未解決が許される」という理由だけで完了扱いにはしません。実装・調査の完了と、個々の対応が確定できないことを区別します。
