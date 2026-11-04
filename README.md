# kanji-kage-map

Unicode漢字・部品、および版を指定したBabelStone PUA識別子から、対応するGlyphWikiのKAGE字形を探し、根拠と確認状態を付けて配布するデータセット。

**[暫定リリース v0.1.0-preview.1](https://github.com/Gai-b63a/kanji-kage-map/releases/tag/v0.1.0-preview.1) を公開しました（2026-11-04）。全109,556識別子を保持していますが、字形一致の確認済み対応は0件です。** Linuxでの再生成・全件検証と、公開配布物のダウンロード照合を完了しました。[公開検証記録](docs/PUBLICATION.md)

## 対象と目的

- 採用Unicode版の全漢字と、BabelStone採用資料に存在する全漢字・全部品を台帳化します。難しい文字や候補がない部品も除外しません。
- BabelStone IDSは対象識別子・部品・出典を列挙する資料として使います。IDS構造をKAGEへ変換するプロジェクトではありません。
- Unicode集合、BabelStoneの見出し集合、IDS内の部品集合、PUA表の集合を別々に保持し、共通部分と差集合を公開します。フォント収録数をIDS収録数の代用にしません。
- 入力はUnicode文字／コードポイント、または提供元・版・PUAコードポイント（必要ならIDS内の番号付き部品ID）です。PUA値単独では識別できません。
- 出力はGlyphWiki名・版、原KAGEデータ、再帰的な依存参照、採用根拠、地域・異体字の差、確認状態です。複数候補と欠落も結果として返します。

完成字形内の筆画へのIDS出現割当、モーフ、ゲーム、漢字図鑑、筆順認定は必須範囲に含めません。

## 対応の意味

`u` + 小文字16進数（最低4桁）のGlyphWiki名は検索の入口です。名前が存在しても字形一致の証明にはなりません。別名、地域字形、異体字、依存参照を検証します。BabelStoneのPUA値をそのまま同値のGlyphWiki名と扱いません。

対応状態は `unreviewed`（未調査）、`candidate`（候補あり）、`matched`（根拠付き確認済み）、`ambiguous`（判断未決）、`missing`（採用資料で候補なし）を基本とします。`missing` は不存在の証明ではなく、探索範囲と日付を持つ調査結果です。描画成功・依存解決成功は別の状態で記録し、対応確認に読み替えません。

Unicode互換漢字やPUAを正規化で統合せず、元の識別子を残します。同じUnicode文字でも地域条件が異なる場合は別候補として保持します。

## 実装と公開への順序

1. 原本を固定し、全件台帳とUnicodeとの差集合を作る。
2. GlyphWikiの既存候補と依存参照を収集する。
3. 例外・PUA・複数字形を根拠付きで整理する。
4. 自動検証と字形レビューを分けて実施する。
5. 再現可能なデータ、ライセンス、監査結果をGitHubで公開する。

具体的な成果物・完了条件・次の実装単位は [段階計画](docs/PLAN.md)、一次資料と未確認事項は [資料調査](docs/SOURCES.md) を参照してください。

## 台帳の生成

Python 3.10以上、外部パッケージ不要。固定原本が手元にある場合はオフラインで生成できます。

```powershell
python -m kanji_kage_map restore --lock sources.lock.json
python -m kanji_kage_map inventory --lock sources.lock.json
python -m unittest discover -s tests -v
```

`restore` は原本がない場合だけ取得し、全ファイルのハッシュを照合します。上流が更新されていると拒否します。初回／更新調査用の取得は `python -m kanji_kage_map acquire --manifest sources.json --lock sources.next.lock.json`。既存lockは上書きしません。取得版の宣言と原文の版が合わない場合は台帳生成を拒否します。

生成物は `data/generated/` の台帳、出現記録、原資料の行、番号付き部品の定義、解析課題、集合差分、集計、SHA-256一覧です。原本と大きな生成物はGitから除外し、取得記録は [sources.lock.json](sources.lock.json) に保持します。

初回実測：109,556識別子（Unicode漢字102,999、Unicode部首・筆画368、資料内のその他Unicode文字38、PUA 6,030、番号付き部品121）。BabelStone IDS見出し97,680件はUnicode漢字集合に含まれ、Unicode側のみが5,319件あります。集合の定義と確認待ちは [台帳監査](docs/INVENTORY-AUDIT.md) を参照してください。すべて字形対応は `unreviewed` です。

## GlyphWiki候補とKAGE参照

公式dumpから最新版2,095,944件・履歴6,622,499件を索引化しました。Unicode識別子103,405件に候補があり、PUA・番号部品6,151件は出典に基づく調査待ちです。全候補は未レビューで、採用済み字形はまだありません。

取得・索引・候補収集・KAGE bundle取得のコマンドと実測は [GlyphWiki監査](docs/GLYPHWIKI-AUDIT.md) に記載しています。`resolve` は版指定を保持して依存KAGEを返しますが、字形の同一性を認定するものではありません。

続行作業でPUA 2,252件の出典IDに基づく候補と全候補の依存監査を追加しました。現在の統合対応表は109,556識別子、うち候補あり105,657件です。**字形一致は全件未レビュー**です。Unicode文字／版付きPUA IDから候補とKAGE一式を取得する方法は [統合対応表の状態と使用方法](docs/MAPPING-STATUS.md) を参照してください。

PUAの公式TTF・WOFF・WOFF2は内部版が1.472で、採用表1.473と不一致でした。6文字の不足を明示し、正解字形としての採用は保留しています。KAGE側のPUA候補2,406字形は空でない有限の描画出力を確認しましたが、字形一致の認定とは別です。[フォント調査と描画検証](docs/FONT-REVIEW.md)

元索引なしで使える独立SQLiteデータセットを公開しました。公開ZIPは約87.5MBです。[配布用データの使用方法](docs/PORTABLE-DATASET.md)。同一環境ではバイト一致、Windows/Linux間では全DB格納値の一致を確認しています。全収録KAGEの追加検査と検索時の所見取得は [静的検査](docs/SYNTAX-AUDIT.md) に記載しています。

## 既存試作との関係

別フォルダのKAGE参照・モーフ試作を読み取り専用で調査しました。対応表は未構築です。そこでの103,067ルート中101,457件の構築成功は別の母集団・別の検査であり、本データセットの対応率ではありません。ゲーム用の筆画形式制限、分割数制限、広い数値範囲による漢字判定を本件へ持ち込みません。

DB・依存パッケージ・キャッシュ・元アーカイブはコピーしていません。既存ファイルも変更していません。

## 出典と権利

主な資料は [BabelStone IDS](https://www.babelstone.co.uk/CJK/IDS.TXT)、[BabelStone PUA](https://www.babelstone.co.uk/Fonts/PUA.html)、[GlyphWiki](https://glyphwiki.org/)、[公式dump](https://glyphwiki.org/dump.tar.gz)、[kurgm/kage-engine](https://github.com/kurgm/kage-engine) です。

独自コードはGPL-3.0-onlyです。データ・フォント・描画エンジンの権利条件は分けて管理し、[NOTICE](NOTICE.md)に記載しています。PUAの原HTML・説明文・フォントは配布データには含めず、識別子と出典参照の事実を記録します。GlyphWiki・Unicode由来データにはそれぞれのライセンス表示を保持します。
