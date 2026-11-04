# 暫定リリースの公開・取得検証（2026-11-04）

[GitHubリポジトリ](https://github.com/Gai-b63a/kanji-kage-map) と [v0.1.0-preview.1](https://github.com/Gai-b63a/kanji-kage-map/releases/tag/v0.1.0-preview.1) を公開しました。確認済み字形一致は0件です。未解決項目を残した候補データの公開であり、全件対応完了ではありません。

## 公開の証拠

公開後に見つかった訂正：[U+EADDの出典ID抽出漏れ](PUA-DISCOVERY-CORRECTION.md)。最新コードでは修正済みですが、このタグの配布物は不変で、旧調査状態を保持します。

- タグ対象コミット：`015a1db1384b0264ddf7929ad21e3e121e0f5809`
- [固定原本からのLinux再生成・全件検証・公開ジョブ](https://github.com/Gai-b63a/kanji-kage-map/actions/runs/41795180715)：成功。
- [39件のPythonテストとNode描画テスト](https://github.com/Gai-b63a/kanji-kage-map/actions/runs/41796556458)：成功。
- [使用例添付の補完ジョブ](https://github.com/Gai-b63a/kanji-kage-map/actions/runs/41796556541)：タグのコードで再生成し、既存チェックサムと一致した2使用例だけを追加。既存添付は置換していません。

ローカルでは独立した開発履歴を保持し、GitHubへは接続APIで同一ツリーを公開しました。公開時のツリーハッシュ一致を確認しています。コミットIDの一致を主張するものではありません。

## 実ダウンロード検証

全9添付を公開URLから取得し、GitHubの添付digestとSHA256SUMSを照合しました。チェックサム一覧の未添付項目は0件です。[取得検証記録](publication-download-verification.json)

オフラインZIPは87,489,970 bytes、SHA-256は `3f56bcf07263561bb21c2ae1cdf888370f78d966a39211844d1561ab9bce7eea`。ZIP内71ファイルをチェックサム照合し、展開したDBをmanifestと照合しました。同梱コードだけで「海/u6d77」と「BabelStone PUA 1.473 E080/uk-20656」の依存KAGE取得を確認しています。[オフライン検証](publication-offline-verification.json)

JSONLアーカイブ内の23ファイルも比較しました。台帳・対応表・両候補群の全依存閉包・静的検査の所見はローカル生成物と一致しています。唯一異なる静的検査集計は入力SQLiteの物理ファイルハッシュの相違を記録したものです。Git管理された出典ロック等は作業ツリーの改行ではなく、Git内の原バイトと比較しました。[JSONL照合](publication-jsonl-verification.json)

## 環境間の再現性

Linux上で取得した原本はすべてロックのサイズ・SHA-256と一致しました。再生成した正本 `mappings.jsonl` のSHA-256もローカルと同じ `aa06be9392495dd1b23c7682ca3ff28697cd272a31122f6caa9b560fa5a86b3c` です。

SQLiteファイルそのものは環境間でバイト一致しませんでした。公開DBのSHA-256は `99d876fce6118a3b80924fd05b3b9c8580ac0496a5db403daba0ac6ff64b3ab6`、ローカル版は `7b235cb838c4abc948086b30e3625092196ba51edef5b12fb1d9782d7eb4df0d` です。全6テーブルをキー順に走査して**すべての格納値の一致**を確認しました。物理的な格納や圧縮の再現性と、レコードの再現性を区別します。[公開manifest](published-manifest.json)

生成時manifestの `status: local-build-only-not-published` は生成コードが出す旧来のフィールド名で、公開済みかどうかを追跡する値ではありません。公開状態は上記のリリースURL・ジョブ・取得検証を根拠にしてください。署名済み真正性の証明は提供していません。

## 残課題

地域・異体字の選択、番号付き部品との対応、PUA表1.473と参照フォント1.472の不一致、静的検査所見の判断、未レビュー字形の比較は継続中です。候補数・参照解決・描画成功を確認済み率には算入しません。最新の検査範囲は [対応状態](MAPPING-STATUS.md)、[静的検査](SYNTAX-AUDIT.md)、[フォント調査](FONT-REVIEW.md) を参照してください。
