# 資料調査と採用判断

調査日：2026-11-04（日本時間）。設立時のDNSエラーは、続行作業でネットワーク利用を許可した取得により解消しました。現在はBabelStoneの3資料とUnicodeの5資料を原バイトで取得・ハッシュ固定済みです。取得URL・日時・SHA-256は [sources.lock.json](../sources.lock.json) を正本とします。以下の表は設立時の観察を残したもので、採用状態は次の更新を優先してください。

## 続行作業での採用確定

- IDS：2025-06-27版、97,680見出しを実測。
- PUA TXT・HTML：1.473版、各6,030見出し。識別子・IDS本文の差は0件。
- Unicode：18.0.0。版付き [ReadMe](https://www.unicode.org/Public/18.0.0/ucd/ReadMe.txt) の正式データ宣言、PropList・Blocksの版ヘッダを実バイトで確認。UnicodeDataと合わせて採用。latest紹介ページのdraft記載ではなく、版付きデータを根拠とした。
- Unicodeの権利文書：[Unicode License V3](https://www.unicode.org/license.txt) を原本として取得・固定。ライセンス本文を取得したことと、本プロジェクトの配布条件確定は区別する。
- GlyphWiki dumpは続行作業で新規取得し、旧試作の記録ハッシュとの一致を実測確認しました。最新版・履歴を索引化し、同梱ライセンスを保存しています。[GlyphWiki監査](GLYPHWIKI-AUDIT.md)を参照してください。PUA資料の再配布条件確認、エンジン導入は未実施。番号付き部品のPUA値の説明はIDS版に属する主張として保存し、1.473版PUAと同一であるとはまだ認定していません。

全件台帳の集計と制限は [台帳監査](INVENTORY-AUDIT.md) に記載しています。

## 一次資料

| 資料 | 確認内容 | 採用・未確認事項 |
| --- | --- | --- |
| [IDS.TXT](https://www.babelstone.co.uk/CJK/IDS.TXT) | ヘッダはUnicode 16.0、2025-06-27、97,680件。本文の範囲説明には15.1・97,058件が残る。番号付き未符号化部品がある | 採用候補。実バイト・全件数・ハッシュは未確認。記述の不整合を実測で照合する |
| [IDS_PUA.TXT](https://www.babelstone.co.uk/CJK/IDS_PUA.TXT) | 表示版1.473、2026-04-08。IDS空欄の行も存在 | PUAページと併用。空欄行を落とさない。ライセンス適用範囲・原本ハッシュ未確認 |
| [PUA表](https://www.babelstone.co.uk/Fonts/PUA.html) | 表示版1.473、6,030字・部品。削除済み値の再利用と版記録の必要性を明記 | TXTとの一致は未集計。古い将来予定の説明も残っており、本文だけから現在のUnicode移行を断定しない |
| [GlyphWiki](https://glyphwiki.org/)・[dump](https://glyphwiki.org/dump.tar.gz) | 今回Webからトップは403。旧試作に公式dumpの取得記録と抽出ライセンスあり | 新規dump取得なし。旧記録は参考情報として保持し、ハッシュ再検証前に採用済みとしない |
| [kage-engine](https://github.com/kurgm/kage-engine) | リポジトリはGPL-3.0表示。旧試作の利用版は0.7.0 | 本プロジェクトには未導入。導入時にタグ・コミット・lock・COPYINGを固定する |
| [Unicode latest](https://www.unicode.org/versions/latest/) | 調査時18.0.0ページへ転送されたが、preliminary draft表示も残る | 最新版の確定根拠として単独使用しない。版付きUCD・ReadMe・公開状態を照合後に採用版を決定する |

BabelStone IDSのヘッダは個人・商用での利用を認め、表示形式に関する権利主張を放棄する旨を記載しています。これは提供者の宣言として記録し、フォントや別ファイル全体へ自動的に適用しません。[原文](https://www.babelstone.co.uk/CJK/IDS.TXT)

フォント本体の条件とIDSデータの条件は別です。[BabelStone Hanの説明](https://www.babelstone.co.uk/Fonts/Han.html)では原版Arphic Public Licenseを示していますが、PUAフォントの採用版に適用される同梱文書は未確認です。PUAフォントや画像の同梱はまだ決めていません。

## 既存試作の読み取り調査

参照先：独立した既存試作 `kage-line-lab`（読み取り専用）。ローカルの絶対パスは公開資料には含めません。

- `README.md`、`MORPH-PROGRESS.md`：KAGE参照の分解・モーフ試作。古い中間値と最終監査が混在するため、今回のカバレッジへ転用しない。
- `database-source.json`：取得日2026-11-04、公式dump SHA-256は `fd3aebc0a3d3d6bdb7c6498e9f2a65f3abe316c23e59ed4a1dd73abd30fa2b72` と記録。これは記録値であり本作業で再計算した値ではない。
- 同記録の取り込み行数：`dump_newest_only.txt` 2,095,940、`dump_all_versions.txt` 6,622,189。Unicode対象数でも対応数でもない。
- `server.py`：Unicode名から99形式の部品を再帰解決する。明示版を保持し循環を検知する設計は参考になる。入力の範囲判定、深さ64・件数2048の制約は試作用であり、本件の対象除外根拠にはしない。
- `build_database.py`：最新・全履歴を索引化するが、3列の中間列を捨て、条件不一致行をスキップする。新しい索引では版情報と取り込み課題の可観測性を確保する。DB内にないものを直ちに上流欠落とみなさない。
- `GLYPHWIKI-LICENSE.txt`：旧試作がdumpから抽出した文書を閲覧。改変・商用を含む利用・複製・配布を認め、無保証とするGlyphWiki Projectの表示を確認。採用dumpに含まれる文書との一致は今後確認する。

巨大な `glyphs.sqlite3` は未走査・未コピー。試作コードも未コピー。旧 `IDS-KAGE-PROJECT-BRIEF.md` は今回のスコープ根拠として使用していません。

## 設立時の状態

作業フォルダは空で、Gitリポジトリではありませんでした。`E:\AGENTS.md`、`E:\GitHub\AGENTS.md`、プロジェクト直下の既存 `AGENTS.md` は存在しませんでした。チャットで提示された方針と引き継ぎ内容を適用し、本プロジェクトの `AGENTS.md` を新規作成しています。

現在は資料ロックと台帳CLIを実装済みです。字形対応件数・対応率は未計測です。
