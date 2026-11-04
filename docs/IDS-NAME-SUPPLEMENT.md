# PUA既存名候補のオフライン検索補足

この補足はPUA全6,030件の調査記録と、4,925字形の指定版原KAGE・依存閉包を含む。候補リンクは4,927件。原典との字形一致は未確認で、既存データセットの確定対応や確認済み率を変更しない。候補のない行、検索対象外の理由も保持する。

## ZIP展開後の使い方

Python標準ライブラリーだけで動作する。元dump、巨大索引DB、ネット接続は不要。

```text
python -m kanji_kage_map lookup-ids-name-leads babelstone:han-pua:1.473:U+E87D --supplement pua-ids-name-supplement.json.gz --manifest pua-ids-name-supplement.manifest.json --output e87d.json
python -m kanji_kage_map lookup-ids-name-leads babelstone:han-pua:1.473:U+E87D --supplement pua-ids-name-supplement.json.gz --manifest pua-ids-name-supplement.manifest.json --glyph u2ff0-u98e0-u76e7@2 --output e87d-kage.json
```

最初の結果に `available_references` と出典行・探索理由が入る。第2の呼び出しは、その名前と版を明示して `bundle` を取得する。`selected_glyph` は常にnullである。`--glyph`の指定は資料の取得要求であり、一致判断や採用指定ではない。PUA値だけの指定や別の版・無関係な候補は拒否する。

## 検証と制限

補足ファイルのSHA-256、スナップショット、対象集合、候補と探索記録の整合、指定版、各原KAGE参照と依存表の対応を読み込み時に検査する。生成時には固定dump索引から各閉包を再取得し、全6,030件の検索と全4,927候補リンクのbundle取得を検証した。追加した検索・破損拒否テストを含め、ローカル全85テスト成功。

既存preview.2の配布DBには、今回必要な字形名・版のうち2,967個がない。この補足はそれらも含めて自己完結する。元DBへ自動マージしない。

`canonical_sha256` は展開JSONのバイト列のハッシュで、圧縮ライブラリーによるgzipヘッダーの差と区別する。配布ファイル自身の検証には `sha256` と `SHA256SUMS` を使用する。コード・GlyphWikiデータ・Unicode/IDS由来の情報の権利区分は同梱LICENSE、NOTICE.md、licensesを参照する。原典ページ画像やフォントは含まない。

## 原本からの再生成

```text
python tools/research_pua_ids_names.py --output data/generated/pua-ids-name-research
python tools/build_ids_name_supplement.py --output dist/pua-ids-name-supplement
python tools/package_ids_name_supplement.py --directory dist/pua-ids-name-supplement
```

固定原本・全件台帳・GlyphWiki索引を先に復元する。これは候補検索を使える形へ整備した補足であり、全件字形レビュー完了版ではない。
