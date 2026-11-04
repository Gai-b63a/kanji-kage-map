# Kanji KAGE Map v0.1 — provisional dataset

Unicode漢字・部品、および版付きBabelStone PUA／番号付き部品の109,556識別子を保持したデータセットです。955,185候補リンクと、依存部品を含む1,201,970件の版付きKAGEを収録しています。

**字形一致の確認済み対応は0件です。** 候補名・出典の一致、参照解決、描画成功は字形一致の保証ではありません。採用PUA表は1.473、取得できた参照フォントは1.472であり、対象版の字形比較に使用できません。候補なし3,899識別子（根拠追加が必要2,966、探索規則で未発見933）も台帳に残しています。依存検査に問題のある候補リンク7件と、取得できない参照先1件を含みます。

## オフラインで使用する

ZIPを展開し、そのフォルダーを作業ディレクトリにします。Python 3.12以降を使用してください。検索・取得に追加パッケージやインターネット接続は不要です。展開後のDBは約1.03 GBあります。

```powershell
python -c "import gzip,shutil; src=gzip.open('kanji-kage-map-v0.1.sqlite3.gz','rb'); dst=open('kanji-kage-map-v0.1.sqlite3','xb'); shutil.copyfileobj(src,dst); dst.close(); src.close()"
python -m kanji_kage_map lookup 海 --dataset kanji-kage-map-v0.1.sqlite3 --output candidates.json
python -m kanji_kage_map lookup 海 --dataset kanji-kage-map-v0.1.sqlite3 --glyph u6d77 --output sea-kage.json
python -m kanji_kage_map lookup babelstone:han-pua:1.473:U+E080 --dataset kanji-kage-map-v0.1.sqlite3 --glyph uk-20656 --output pua-kage.json
```

最初の検索は候補と根拠・確認状態を返します。`--glyph` を付けると記録された固定版から依存KAGEを含む束を返します。この指定は正解の認定やレビュー状態の変更をしません。PUAの提供元・版は省略できません。

## 検証する

`SHA256SUMS` は同梱ファイルすべてのSHA-256です。配布元に掲載するZIP自体のハッシュとも照合してください。ZIP内のチェックサムだけでは配布元の真正性を証明できません。

```powershell
python -c "import hashlib,pathlib; entries=[line.split('  ',1) for line in pathlib.Path('SHA256SUMS').read_text().splitlines()]; bad=[name for expected,name in entries if hashlib.file_digest(open(name,'rb'),'sha256').hexdigest()!=expected]; print('mismatches:',bad); raise SystemExit(bool(bad))"
python tools/verify_release.py kanji-kage-map-v0.1.sqlite3 --output verification.json
```

全件検証は台帳・対応表のID一致、候補の固定版の存在、依存参照と欠落理由、SQLite内部整合性を検査します。字形一致やKAGE命令の完全な意味検査は行いません。

## 出典・利用条件

[NOTICE.md](../NOTICE.md) と [GlyphWikiライセンス](../licenses/GLYPHWIKI.txt)、[Unicodeライセンス](../licenses/UNICODE.txt) を保持してください。コードはGPL-3.0-onlyです。コードのライセンスをすべての上流データへ一括適用していません。元のPUA HTML・説明文・フォント・原アーカイブは同梱していません。詳細は `docs/MAPPING-STATUS.md`、`docs/FONT-REVIEW.md`、原本ロックに記録しています。

この文書はZIP内ではREADME.mdとして配置されます。ZIP内の利用条件は同じフォルダーのNOTICE.md、licenses/以下を参照してください。リポジトリ公開・ダウンロード検証が完了するまではローカル配布候補です。
