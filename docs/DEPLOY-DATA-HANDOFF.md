# サイト初版向けデータ・ライセンス引き継ぎ

2026-11-04（JST）。司令塔からの依頼に基づく固定入力。未対応PUAを含む状態で初版を公開できる。全件字形一致やKAGE対応の完了を公開条件にしない。サイト担当・軽量化担当は、以下を読み取り専用の入力として使用する。

## 採用版と取得先

機械可読の正本は [deploy-data-manifest.json](deploy-data-manifest.json)。5資材の公開URL、絶対ローカルパス、バイト数、SHA-256、ライセンス6ファイルを記録した。2026-11-04にローカル実体を再ハッシュして全11資材を照合した。

| 役割 | 採用版・ファイル | 公開URL |
| --- | --- | --- |
| 全識別子・既存候補の基礎DB | preview.2 / `kanji-kage-map-v0.1.0-preview.2.sqlite3.gz` | [取得](https://github.com/Gai-b63a/kanji-kage-map/releases/download/v0.1.0-preview.2/kanji-kage-map-v0.1.0-preview.2.sqlite3.gz) |
| 基礎DB manifest | preview.2 / `kanji-kage-map-v0.1.0-preview.2.manifest.json` | [取得](https://github.com/Gai-b63a/kanji-kage-map/releases/download/v0.1.0-preview.2/kanji-kage-map-v0.1.0-preview.2.manifest.json) |
| 追加PUA候補と原KAGE閉包 | ids-leads.1 / `pua-ids-name-supplement.json.gz` | [取得](https://github.com/Gai-b63a/kanji-kage-map/releases/download/v0.1.0-ids-leads.1/pua-ids-name-supplement.json.gz) |
| 補足manifest | ids-leads.1 / `pua-ids-name-supplement.manifest.json` | [取得](https://github.com/Gai-b63a/kanji-kage-map/releases/download/v0.1.0-ids-leads.1/pua-ids-name-supplement.manifest.json) |
| サイト参考表示用の未改変WOFF | 実体1.472 / `BabelStoneHanPUA.woff` | [公式取得先](https://www.babelstone.co.uk/Fonts/WOFF/BabelStoneHanPUA.woff) |

主要ローカルパス（既存実体なので新規巨大生成不要）:

- 基礎圧縮DB: `E:/GitHub/kanji-kage-map/.cache/corrected-published/kanji-kage-map-v0.1.0-preview.2.sqlite3.gz`
- 基礎展開DB: `E:/GitHub/kanji-kage-map/.cache/corrected-published/offline/dataset.sqlite3`
- 基礎manifest: `E:/GitHub/kanji-kage-map/.cache/corrected-published/kanji-kage-map-v0.1.0-preview.2.manifest.json`
- 補足: `E:/GitHub/kanji-kage-map/.cache/ids-name-published/pua-ids-name-supplement.json.gz`
- 補足manifest: `E:/GitHub/kanji-kage-map/.cache/ids-name-published/pua-ids-name-supplement.manifest.json`
- WOFF: `E:/GitHub/kanji-kage-map/data/raw/275aa35448ab1e214e9c9e9a5cd0622dc20db8c1c2e3a1d8302a9696b52b6f34/BabelStoneHanPUA.woff`

基礎圧縮DBは87,186,205バイト、SHA-256 `ac49c3a853ebac387424482e1509871b7076b3246c14987eaa526a727da084d9`。展開DBは `4cb1ba08625e6a6771589304cfe214573c18165f32b59c68cdbc3054847cd0aa`。

補足は1,408,164バイト、SHA-256 `1ed9ec5bc1aa3c4405b30ef5b782136a4d1e2a0b1b766aab405ac658964a296e`。圧縮前JSONは `6e926aaee42e1383074e66efc73cf99f4f42fcb04d6c7e8c8489de25cc1a5e29`。ローカル再生成版のgzipは圧縮環境により異なるため、サイト投入には上記の公開実取得物を採用する。

## 優先順位とデータ契約

1. 母集団・識別子・既存候補・既存レビューの正本はpreview.2。109,556識別子（PUA6,030、番号部品121を含む）を保持する。`unicode:U+...` と `babelstone:han-pua:1.473:U+...` を混同しない。
2. 補足は全PUA6,030行、4,927候補リンク、4,925指定版字形を追加の調査集合として提示する。既存候補や検索状態を上書きしない。基礎DBにない字形版2,967個もあるため、補足のbundleを読む経路が必要。
3. 候補をまとめて表示する場合、キーは少なくとも `(entity_id, snapshot_sha256, glyph_name, revision)`。同じキーでも根拠の集合を保持する。別名やSVG一致による自動統合・同一字形認定をしない。
4. 基礎DBの `selected_glyph` と全体の未レビュー状態を保持する。補足は `evidence_kind=existing_ids_name_lead_only`、`review_status=unreviewed`、`selected_glyph=null`。クリック・描画成功・補足追加を「一致確認」にしない。
5. preview.2の3件のAIレビューは典拠・候補版・判定基準に限定された履歴。「一」の一条件での一致、「海」の差異／判断不足を全体の確認済み率に置き換えない。
6. 両データのGlyphWikiスナップショットは `fd3aebc0a3d3d6bdb7c6498e9f2a65f3abe316c23e59ed4a1dd73abd30fa2b72`。版なし依存の解決先もこのスナップショット内の版として表示する。
7. 基礎候補あり105,657、候補なし934、出典根拠必要2,965は基礎DBの集計。補足あり4,925は別集計。母集団・重複を考慮せず加算しない。候補なし・依存問題・フォント欠字の項目も表示から落とさない。

## 起動可能な取得・検索例

作業ディレクトリは `E:/GitHub/kanji-kage-map`。Python標準ライブラリーのみで動く。

```powershell
python tools/fetch_deploy_data.py --verify-local
# 別環境で取得する場合。既存ファイルも必ずハッシュ照合する。
python tools/fetch_deploy_data.py --output .cache/deploy-data

# 既存展開DBを用いた「海」の検索
python -m kanji_kage_map lookup U+6D77 --dataset .cache/corrected-published/offline/dataset.sqlite3 --output .cache/deploy-sea.json

# 補足のみでE87Dの原KAGEと依存先を取得
python -m kanji_kage_map lookup-ids-name-leads babelstone:han-pua:1.473:U+E87D --supplement .cache/ids-name-published/pua-ids-name-supplement.json.gz --manifest .cache/ids-name-published/pua-ids-name-supplement.manifest.json --glyph u2ff0-u98e0-u76e7@2 --output .cache/deploy-e87d.json
```

新規取得した圧縮DBは `gzip.open` と `shutil.copyfileobj` で一度だけ展開し、manifestの展開DBハッシュを照合する。軽量化担当は固定入力を投影・圧縮してよいが、原KAGE、版、全識別子、根拠、状態を損失なく保持し、その出力独自のmanifestと照合結果を付ける。

## サイト同梱と必要表示

| 資材 | 初版の扱い・必要ファイル |
| --- | --- |
| GlyphWiki原KAGE・派生表示 | 配布可。Copyright 2009 GlyphWiki Project、無保証を示し、`licenses/GLYPHWIKI.txt`全文を提供する |
| Unicode由来の台帳 | `licenses/UNICODE.txt`の著作権・許諾・無保証をデータまたは付属文書に保持する |
| BabelStone IDS・識別子・出典ID事実 | Andrew Westおよび原資料への出典リンク、固定版を表示。原PUA表HTML・説明文の丸ごと転載はしない |
| このプロジェクトのコード | GPL-3.0-only。`LICENSE`、`NOTICE.md`、配信コードに対応するソースの取得リンクを提供する |
| ブラウザー内KAGEエンジンを配布する場合 | 固定版と著作権表示、`licenses/KAGE-ENGINE-GPL-3.0.txt`、配信したコードに対応するソース／変更を取得できるようにする。KAGEデータの条件とは別扱い |
| BabelStone Han PUA WOFF | 公式Download節にWOFF自己ホスト許可あり。初版は上記固定WOFFを未改変で配信し、`licenses/ARPHICPL.txt`全文を同梱する。フォント内部の名前・著作権・許諾を保持。サブセット化・再変換は今回の固定資材案に含めない |

公式根拠: [PUAページDownload節](https://www.babelstone.co.uk/Fonts/PUA.html#Download)（2026-11-04確認）。同ページは自己ホストと個人・商用利用を案内している。WOFF実体のname tableを再検査し、埋込ARPHIC PUBLIC LICENSEが `licenses/ARPHICPL.txt` と改行正規化後に一致することを確認した。ARPHIC §1は未改変ライセンス文書の保持を条件とする。フォントの著作権表示は「(c) Copyright 1994-1999, Arphic Technology Co., Ltd.; (c) Copyright 2009-2025, Andrew West.」。

`NOTICE.md`の「フォントをデータ配布物に含めない」は既存DB/ZIPの方針であり、公式許可に基づく今回のサイト別資材の自己ホストを禁止する記述ではない。既存配布物のNOTICEは書き換えず、サイトのライセンス画面にこの追加資材を明示する。全資材に一括でGPLだけを適用したとは表示しない。

ライセンスのローカル原本は `E:/GitHub/kanji-kage-map/LICENSE`、`E:/GitHub/kanji-kage-map/NOTICE.md`、`E:/GitHub/kanji-kage-map/licenses/`。manifestには各ファイルの固定コミットURLとハッシュを付けた。Windowsの改行差のため、ローカル実体ハッシュとGitHub固定原本ハッシュを区別している。文章を変更する必要はない。

## フォントの版差・欠字

台帳はBabelStone Han PUA 1.473。取得済みWOFFのname tableは **1.472**、PUA収録数は6,024。公式の表示版1.473を実体版に上書きしない。WOFF SHA-256は `275aa35448ab1e214e9c9e9a5cd0622dc20db8c1c2e3a1d8302a9696b52b6f34`、2,257,136バイト。

欠字は **E87B、E87C、E87D、E87F、F55A、F55B**。該当行には「参考フォント未収録」を表示し、別フォントへのフォールバックを正解字形と扱わない。ほかの6,024件も版一致・字形一致の確定ではなく参考表示。端末に入った別版を優先するCSS `local()` は使わず、固定ファイルをロードする案が適する。

## 公開検証と担当境界

- 基礎版: [公開検証](CORRECTED-PUBLICATION.md)。全6添付、ZIP170ペイロード、全DB論理レコードを検証済み。
- 補足版: [公開検証](IDS-NAME-PUBLICATION.md)。全5添付、ZIP32ペイロード、全検索を検証済み。
- 補足公開検証記録のmain反映は復旧済み。GitHub mainの `81cf1dc63f5b5b389a03b0c85065dcf08ffcf4c0` を実読して確認した。
- 本担当はサイト画面・デプロイ・軽量化領域を編集していない。サイトの公開URLでの動作確認はサイト担当と司令塔が実施する。本資料の未レビュー・欠字は初版公開の停止条件ではない。
