# 独立配布用データセット

[暫定リリース v0.1.0-preview.1](https://github.com/Gai-b63a/kanji-kage-map/releases/tag/v0.1.0-preview.1) を公開し、実ダウンロードも検証しました。[公開・再現性の記録](PUBLICATION.md)を参照してください。以下の92MBとハッシュは当初のWindowsローカル生成物の記録です。公開Linux版はgzip 87,183,731 bytesで、[公開manifest](published-manifest.json)に別のハッシュを記録しています。全DB格納値は一致しています。

## 内容

`dist/kanji-kage-map-v0.1.sqlite3.gz` を展開すると、元のGlyphWiki索引なしで使えるSQLiteデータベースになります。通常の検索・KAGE取得にはPython標準ライブラリだけを使います。描画を行う場合のみ、別途KAGEエンジンを利用します。

| 項目 | 件数／サイズ |
| --- | ---: |
| 台帳 | 109,556識別子 |
| 対応状態レコード | 109,556件 |
| 候補リンク | 955,185件 |
| 版付きKAGE | 1,201,970件 |
| 依存参照 | 1,810,938件 |
| 格納できない参照先 | 1件（理由を保持） |
| SQLite | 1,033,977,856 bytes |
| gzip | 92,085,494 bytes |

候補には地域・異体字・関連字欄の探索結果も含みます。全候補が正解字形であるという意味ではありません。全字形一致は未レビューで、選択済み字形は設定していません。PUAの版不一致と未解決項目も残しています。

## 取得と利用

検索コード・監査資料・利用条件を含むオフラインZIPも生成できます。

```powershell
python tools/package_release.py
```

ZIP内のREADMEに展開・検索・検証手順を収録しています。パッケージ生成時にgzipのハッシュとサイズをmanifestと照合し、全同梱ファイルのチェックサムを付けます。元アーカイブやフォント、インストール済みパッケージは含めません。同一入力からのZIPのバイト一致、全同梱ファイルと展開DBのハッシュ、別フォルダーでのUnicode・PUA検索を確認しました。これは公開後のダウンロード検証とは別です。

公開後の配布では、データとともに `NOTICE.md`、`licenses/GLYPHWIKI.txt`、`licenses/UNICODE.txt` を同梱します。元のPUA HTML・説明文・フォント・原アーカイブは配布物に含めません。利用条件の区別は [NOTICE](../NOTICE.md) に記載しています。

展開後、リポジトリのコードで次のように取得できます。

```powershell
python -m kanji_kage_map lookup 海 --dataset dist/kanji-kage-map-v0.1.sqlite3 --output result.json
python -m kanji_kage_map lookup 海 --dataset dist/kanji-kage-map-v0.1.sqlite3 --glyph u6d77 --output sea-kage.json
python -m kanji_kage_map lookup babelstone:han-pua:1.473:U+E080 --dataset dist/kanji-kage-map-v0.1.sqlite3 --glyph uk-20656 --output pua-kage.json
```

候補選択なしでは根拠・版・確認状態の一覧を返します。`--glyph` では候補の固定版から依存KAGEまでを取り出します。海は `u6d77@19`、PUA E080の候補は `uk-20656@4` の取得を確認しました。これは字形の同一性を確定する操作ではありません。

SQLiteテーブルは `inventory`、`mappings`、`glyphs`、`dependencies`、`issues`、`metadata`。台帳・候補・KAGEはJSONを保持し、依存辺は元参照名と固定された参照先を別列で保持します。metadataには採用snapshot、原本ロック、生成入力のハッシュ、件数、生成完了状態が入ります。

## 再生成と検証

```powershell
python -m kanji_kage_map build-release
python tools/verify_release.py dist/kanji-kage-map-v0.1.sqlite3 --output docs/portable-verification.json
```

元台帳と依存監査の出力を入力に生成します。既存DBは上書きしません。再生成には別の `--output` を指定します。

全台帳IDと対応表IDの一致、955,185候補すべての固定版の存在、KAGEの名前・版・snapshot、全依存辺、SQLite内部整合性を検査しました。欠落参照は `lp_lps-00001460@1` の1行目が指す `lp_lpy-00001460` の1件です。[全件検証](portable-verification.json)

別出力先へ全件をもう一度生成し、SQLiteとgzipの両方がバイト単位で一致しました。gzipの時刻・埋め込みファイル名を固定しています。同じ環境・固定入力での結果であり、異なるSQLite/Python版間のバイト一致は未確認です。[生成manifest](portable-manifest.json)

SQLite SHA-256：`7b235cb838c4abc948086b30e3625092196ba51edef5b12fb1d9782d7eb4df0d`

gzip SHA-256：`625ac65f482e2d0ab932226a7f4cf0d61e270b4e702ca5354802a4174bbdc0ac`

公開ファイル一式・公開URL・ダウンロード後のチェックサムを確認済みです。ZIP内コードによる独立検索も検証しました。物理ファイルのハッシュは取得元に対応するmanifestを使用してください。
