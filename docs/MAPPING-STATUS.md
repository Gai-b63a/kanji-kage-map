# 統合対応表と依存監査（2026-11-04）

追記：独立配布DB・オフラインパッケージは[暫定公開・実取得検証済み](PUBLICATION.md)です。末尾の「残る公開条件」は公開前時点の記録です。追加の[全収録KAGE静的検査](SYNTAX-AUDIT.md)では418字形に要確認事項を検出しました。以下の依存監査7候補という件数は、座標検査などを含む総合的な正常数を意味しません。

続行作業でPUA候補全2,406字形の描画検査と、公式フォント3形式の内部版確認を実施しました。採用表1.473と配布フォント1.472の不一致があります。[フォント調査](FONT-REVIEW.md)を参照してください。以下は対応表・参照監査の記録で、字形一致のレビューとは分けています。

## 現在取得できるもの

全109,556識別子を保った暫定対応表を `data/generated/mappings.jsonl` に生成しました。105,657識別子に候補があり、933件は今回の出典ID検索規則では候補なし、2,966件は出典の追加調査が必要です。後者2集合には版付きPUAと番号付き部品を含みます。未確認を「欠落確定」に変更していません。

候補リンクは955,185件。確認済みの字形一致は0件です。[集計](mappings-summary.json)

対応表には候補名・版・取得規則・根拠となる資料位置、依存解決状態、未解決理由、字形差のレビュー状態を記録します。Unicode名、関連字欄、出典IDの一致だけで採用字形を決定しません。`selected_glyph` はnull、`glyph_difference_status` はunreviewedです。

## Unicode候補の全依存監査

候補リンク952,775件を重複排除した951,164字形について、採用snapshot内の依存閉包を走査しました。参照ノード1,199,016件、依存辺1,807,364件。うち1参照は欠落しており、取得できたKAGEレコードは1,199,015件です。

- 951,157候補は今回の依存・命令タグ検査に課題なし。
- 6候補に不正な命令タグの影響、1候補に参照切れの影響あり。
- 到達可能な循環は検出されませんでした。

[監査集計](dependency-summary.json)と[影響する7候補](candidate-dependency-issues.json)を保存しています。不正タグの実体は空タグや `s`。参照切れは `lp_lpy-00001460`。これらを削除・補完して成功扱いにはしていません。

監査は版指定と参照の検査、および数字でない命令タグの検出です。全座標・全KAGE命令の意味検証、描画成功、字形一致を証明するものではありません。

## PUAの出典に基づく候補

BabelStone PUA 1.473の表の **Source Refs列** から識別子を抽出し、GlyphWikiの同名候補を調査しました。説明文中の別字への言及やPUA符号位置はこの結合には使っていません。各候補に原資料の行、出典ID、列名、原資料のリンクを保存しています。

2,252のPUA識別子から2,410候補リンクを取得しました。重複排除した2,406字形について8,278依存ノード・10,149依存辺を走査し、今回の参照検査では課題0件です。[候補集計](pua-summary.json)、[依存監査](pua-dependency-summary.json)

例：`babelstone:han-pua:1.473:U+E080` は表の `UK-20656` を根拠に `uk-20656@4` を候補取得できます。これは同名出典IDによる候補であり、PUAフォントとKAGEの目視一致を確認済みという意味ではありません。

## 再生成と検索

台帳・GlyphWiki索引・Unicode候補を生成した後に実行します。

```powershell
python -m kanji_kage_map pua-candidates
python -m kanji_kage_map audit-dependencies
python -m kanji_kage_map audit-dependencies --candidates data/generated/pua-research/pua-candidates.jsonl --output data/generated/pua-research/dependency-audit
python -m kanji_kage_map assemble
python -m kanji_kage_map lookup U+6D77 --output data/generated/sea-candidates.json
python -m kanji_kage_map lookup 海 --glyph u6d77 --output data/generated/sea-kage.json
python -m kanji_kage_map lookup babelstone:han-pua:1.473:U+E080 --glyph uk-20656 --output data/generated/pua-e080-kage.json
```

`lookup` は候補を一覧で返します。`--glyph` を付けると、その候補の固定版と依存KAGEを取得します。利用者による選択は字形一致のレビューとは別扱いです。候補にない字形、台帳にないID、版を欠くPUA、snapshotが違う索引は拒否します。

`assemble` は候補ファイルのハッシュと依存監査のsnapshot、監査結果ファイルのハッシュを照合し、未監査の候補があれば失敗します。元台帳にないPUAや重複IDも拒否します。

## データ契約

JSON Schema Draft 2020-12を `schemas/` に定義しました。現行0.1の台帳・候補・暫定対応表・KAGEレコード・依存辺・候補依存状態が対象です。確認済み対応を扱う将来版では、根拠・レビュー決定を必須とする契約へ更新します。現在の契約で `matched` と偽装した行は受け入れません。

検証用ライブラリは通常の生成CLIには不要です。任意の検証環境に `requirements-validation.txt` を導入してください。この作業ではプロジェクト内 `.cache/validation` に導入しました。

```powershell
python -m pip install --target .cache/validation -r requirements-validation.txt
python tools/validate_data.py schemas/inventory.schema.json data/generated/inventory.jsonl --output docs/validation-inventory.json
python tools/validate_data.py schemas/mappings.schema.json data/generated/mappings.jsonl --output docs/validation-mappings.json
```

検証結果は `docs/validation-*.json` に入力ハッシュ・スキーマハッシュ・検査行数とともに保存します。構造検証は字形の意味の検証と区別します。

## 残る公開条件

29テストで版参照・循環・共有依存・欠落の伝播、PUA版必須、候補選択、監査後の改変拒否等を検査しました。全件監査に加えて、海の `u6d77@19` とPUA E080の候補 `uk-20656@4` の依存KAGE取得を実行確認しています。

地域・異体字の選択基準、字形の目視比較、番号部品とPUAの版対応、PUA資料の再配布条件、描画検証、再現可能な公開パッケージとGitHub公開が残っています。接続中のGitHubアカウントで同名リポジトリを照会した結果は404でした。公開準備後に作成または公開先を確定する必要があります。現時点で公開済みとは報告しません。
