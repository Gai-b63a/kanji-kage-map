# 「海」の地域別典拠とKAGEの特徴比較

2026-11-04、CodexがUnicode 18.0の公式コード表と固定版KAGEの描画を目視比較しました。対象はU+6D77「海」の8候補と、右下の内部筆画という一つの構造特徴です。字形全体の輪郭一致や、他の文字・候補の一致を認定するレビューではありません。

## 一次資料と観察

[Unicode 18.0 CJK統合漢字コード表](https://www.unicode.org/Public/18.0.0/charts/PDF/U4E00.pdf) のPDF206ページ（印刷ページ762）に、G0-3A23、HB1-AEFC、T1-5640、J0-3324、K0-7A2D、KP0-F5C3、V1-5C49の典拠字形が並びます。原PDFのSHA-256は `9c2527a34623870413a348778a7804475c15e92960017dd3693ba18fd121aaf9` です。取得記録は [review-unicode-charts.lock.json](../review-unicode-charts.lock.json) に保存しました。

日本典拠J0-3324では右下の内部が連続した縦線、他の6典拠では二つの点になっていることを確認しました。

| 固定KAGE候補 | 比較した典拠 | 確認した内部筆画 |
| --- | --- | --- |
| u6d77@19 | J0-3324 | 縦線：特徴一致 |
| u6d77-j@10 | J0-3324 | 縦線：特徴一致 |
| u6d77-g@9 | G0-3A23 | 二つの点：特徴一致 |
| u6d77-h@6 | HB1-AEFC | 二つの点：特徴一致 |
| u6d77-t@4 | T1-5640 | 二つの点：特徴一致 |
| u6d77-k@14 | K0-7A2D | 二つの点：特徴一致 |
| u6d77-kp@4 | KP0-F5C3 | 二つの点：特徴一致 |
| u6d77-v@11 | V1-5C49 | 二つの点：特徴一致 |

一方、一般名 `u6d77@19` とG0-3A23を比べると、この特徴は不一致です。一般名の原KAGEは日本字形への参照であり、一般名だけを理由に全地域共通の字形として選ぶことはできません。

固定snapshot内では、一般名と-j、-hと-t、-gと-kpと-vの各群は描画SVGのハッシュも同一でした。この同一性は**当該KAGE描画同士**についての結果であり、Unicode表の各典拠が同一の輪郭であるという意味ではありません。太さ・端部・字面の比率などの差を、この一特徴の確認で無視していません。Unicodeの表紙も、参照字形は実際のフォントの形を一律に規定しないと説明しています。

## 記録と利用

[unicode-sea-review.json](unicode-sea-review.json) に、レビュー者・日付・資料版・ページ・典拠ID・固定KAGE版・描画SVGハッシュ・観察・判定範囲を保存しています。8件の特徴一致と1件の特徴不一致です。`full_glyph_match_status` は `not_determined`、`selected_glyph` はnullです。

最新のリポジトリコードでは、既存の公開DBを使って観察記録を取得できます。v0.1.0-preview.1の同梱コードにはこの後追加されたオプションがないため、最新コードを使用してください。

```powershell
python -m kanji_kage_map lookup U+6D77 --dataset path/to/kanji-kage-map-v0.1.sqlite3 --glyph u6d77 --feature-reviews docs/unicode-sea-review.json --output sea-reviewed.json
```

`feature_reviews` に該当する観察が入り、既存の対応判定や全体の未レビュー状態は変わりません。snapshot不一致、候補版の不一致、一特徴から全体一致へ昇格する記録、観察と判定の矛盾は拒否します。外部から渡されたレビュー記録の真正性を署名検証する機能ではありません。

再描画用の束は次の手順で作れます。これは観察判断を自動で再実行するものではありません。

```powershell
python tools/prepare_feature_review.py docs/unicode-sea-review.json --dataset path/to/kanji-kage-map-v0.1.sqlite3 --output data/generated/review/sea-bundles.json
node tools/render_bundles.mjs data/generated/review/sea-bundles.json data/generated/review/sea-rendered.json
```

8候補すべての再描画SVGハッシュを記録値と照合しました。描画エンジンは固定した `@kurgm/kage-engine@0.7.0`、`kUseCurve=false` です。

PDF・PDFからの画像・埋め込みフォントは再配布しません。コード表はローカルで参照し、公開するのは識別子・出典位置・自分の観察記録です。コード表の利用条件と、UnicodeData由来の台帳の利用条件は同一視しません。
