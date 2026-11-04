# レビュー補足版の公開・実取得検証

2026-11-04、[v0.1.0-review.1](https://github.com/Gai-b63a/kanji-kage-map/releases/tag/v0.1.0-review.1) を公開しました。タグ対象は `1e9cc743169a4f606d5c8db4a4d99d2b9dbddf2b`。初回候補データを保持し、レビュー3件を加えた補足版です。全件字形レビュー完了や候補再生成版ではありません。

[GitHub上の生成・全レコード検証・展開後検索・公開ジョブ](https://github.com/Gai-b63a/kanji-kage-map/actions/runs/41809159410) が成功しました。通常のテスト63件も同ジョブ内で成功しています。初回Releaseの添付を置き換えていません。

## 配布物と検証

公開APIが返す全6添付を、公開URLからダウンロードしました。

- オフラインZIP、圧縮SQLite、manifest。
- 「一」と「海」のレビュー付き検索例。
- 外部SHA256SUMS。

各添付のサイズとSHA-256をGitHubのasset digest、およびチェックサム一覧と照合しました。ZIP内152ペイロードファイルもすべて照合しました。[取得検証記録](review-release-download-verification.json)

ZIPを展開し、同梱コードだけで「一」の構造一致判断、「海」の差異／証拠不足判断、PUA E0C7→Unicode U+32580→u32580@3のKAGE取得を実行しました。元mappingのselected_glyphはnullのままです。[オフライン検証](review-release-offline-verification.json)

展開したDBの全109,556台帳行・109,556対応行・1,201,970KAGE行・1,810,938依存行・4問題行を、元の初回公開DBとキー順に比較し、全値一致を確認しました。元メタデータの値も不変です。

## ハッシュと再現性

[公開manifest](review-release-published-manifest.json)は、公開DBのSHA-256を `cb3ed19a8cf351e562a84ec92f6e5fab29c09b39dfe0d1b7d414a7b9f12a17cf` と記録しています。ダウンロード・展開した実体と一致しました。

Windowsで先に生成したDBの物理ハッシュとは異なります。Linux公開版も同じ元DBから生成し、全元レコードを保存したことを独立に確認しています。レビュー履歴のUTF-8ハッシュは双方とも `3d16ef0af168cec418d1b9b46848c2a81286b077438a158d24718fbbe27484d3` です。SQLiteの物理ファイルや圧縮物の環境間バイト一致は主張しません。

コードと同梱資料はタグのコミットで固定されています。再生成は `tools/package_reviewed_release.py`、実ダウンロード検証は `tools/verify_review_release_download.py` で行います。生成に使う元DBは初回公開版のSHA-256まで固定し、異なる入力は拒否します。

## 残る制限

構造一致1件はU+4E00、u4e00@46、日本典拠J0-306Cという範囲限定のAI判断です。元の候補・選択状態と全体coverageは初回版のままであり、範囲を外して全件の確認済み件数に読み替えません。

U+EADDの抽出訂正は文書と追加典拠照合には反映されていますが、基礎mapping行を修正した再生成版ではありません。PUA表とフォントの版差、全体のレビュー、判断の集計・共通スキーマ化も未完了です。
