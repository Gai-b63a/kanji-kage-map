# フォント欠落6字の原典到達状況

2026-11-04。固定PUA表1.473の原典リンクを実際に調べた。[識別子別記録](pua-missing-font-source-access.json)。今回、対象字形の画像を確認できた行は0件であり、対応の確認状態は変更していない。

| 対象 | 到達状況 | 次の調査 |
| --- | --- | --- |
| E87B・E87C | 国家図書館の閲覧先はHTMLとして応答したが、テキスト取得では読める内容なし。画像未確認 | 対話的な閲覧画面で巻229・16aと画像ID10035849を照合 |
| E87D | Harvardの閲覧先・公式手順で導いたmanifestとも直接取得はHTTP 403 | 同じDRS IDの公開複製の実体とページ対応を確認 |
| E87F | Commonsの資料説明ページは確認。指定1398ページの画像は未確認 | 原本PDFのページと巻32・13aを照合 |
| F55A・F55B | 固定表の原典・出典ID欄が空欄 | 別の典拠を探す。IDSだけから字形を確定しない |

Harvardの[公式案内](https://library.harvard.edu/services-tools/iiif-manifests-digital-objects)に従い、閲覧URLから `/view` と `$` 以降を取り除いて `https://iiif.lib.harvard.edu/manifests/drs:428496451` を導いた。このURLも403だった。認証・アクセス制限の回避はしていない。

[Commonsの公開複製目録](https://commons.wikimedia.org/wiki/Commons:Library_back_up_project/file_list/Harvard-Yenching/1)には `File:Harvard drs 428496451 潛確居類書 v.34.pdf` が載る。同じDRS番号を持つ調査先として記録したが、ファイル実体の同一性、画像順序、指定35画像目との対応は未確認。目録の一致を原典画像の確認済み扱いにはしない。

[CommonsのSBL064資料説明](https://commons.wikimedia.org/wiki/File:SBL064_%E5%A4%96%E8%87%BA%E7%A7%98%E8%A6%81%E6%96%B9.pdf)は閲覧でき、当該書籍PDFの存在を確認できた。説明ページの確認と、対象字形の載るページの確認は別の段階として保持する。

これらは現在の環境での到達結果で、原典が一般に存在しない、すべての利用者に閲覧不能、という主張ではない。別資料や異なる版を同一視せず、原典画像と所在を照合してから次の字形レビューへ進む。
