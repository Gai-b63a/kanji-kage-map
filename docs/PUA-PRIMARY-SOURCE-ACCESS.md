# フォント欠落6字の原典到達状況

2026-11-04。固定PUA表1.473の原典リンクを実際に調べた。[識別子別記録](pua-missing-font-source-access.json)。E87Dについて公開複製のページ画像を取得・目視確認した。対象字形・丁番号・版の一致を確定した行はまだ0件であり、対応の確認状態は変更していない。

| 対象 | 到達状況 | 次の調査 |
| --- | --- | --- |
| E87B・E87C | 国家図書館の閲覧先はHTMLとして応答したが、テキスト取得では読める内容なし。画像未確認 | 対話的な閲覧画面で巻229・16aと画像ID10035849を照合 |
| E87D | Harvard直接取得はHTTP 403。Commons API経由で複製の35ページ画像を取得・目視確認 | 巻96・25bとの対応、対象文字と版を確定 |
| E87F | Commonsの資料説明ページは確認。指定1398ページの画像は未確認 | 原本PDFのページと巻32・13aを照合 |
| F55A・F55B | 固定表の原典・出典ID欄が空欄 | 別の典拠を探す。IDSだけから字形を確定しない |

Harvardの[公式案内](https://library.harvard.edu/services-tools/iiif-manifests-digital-objects)に従い、閲覧URLから `/view` と `$` 以降を取り除いて `https://iiif.lib.harvard.edu/manifests/drs:428496451` を導いた。このURLも403だった。認証・アクセス制限の回避はしていない。

[Commonsの公開複製目録](https://commons.wikimedia.org/wiki/Commons:Library_back_up_project/file_list/Harvard-Yenching/1)には `File:Harvard drs 428496451 潛確居類書 v.34.pdf` が載る。同じDRS番号を持つ調査先として記録したが、Commons公開APIでは165ページ・143,297,753バイトのPDF情報を取得できた。APIが返した35ページ目のJPEG（1920×1608、820,429バイト）も取得・目視確認した。SHA-256は `b676603dee5bb0b8bba49a1813af93b80de92747e4b71d67f90d77892b14f052`。見開き本文の飲饌部を確認したが、巻96・25bとの厳密な対応と対象字の同定は未確定。[取得・観察記録](pua-e87d-source-image.json)にURL、ハッシュ、画像内の調査位置を保存した。PDF全体は取得しておらず、APIのPDF SHA-1は報告値として区別する。

[CommonsのSBL064資料説明](https://commons.wikimedia.org/wiki/File:SBL064_%E5%A4%96%E8%87%BA%E7%A7%98%E8%A6%81%E6%96%B9.pdf)は閲覧でき、当該書籍PDFの存在を確認できた。説明ページの確認と、対象字形の載るページの確認は別の段階として保持する。

これらは現在の環境での到達結果で、原典が一般に存在しない、すべての利用者に閲覧不能、という主張ではない。別資料や異なる版を同一視せず、原典画像と所在を照合してから次の字形レビューへ進む。

## 画像取得時の注意

MediaWikiの `imageinfo` に `iiurlparam=page35-4000px` を指定した応答は幅4000・高さ3348を報告したが、返されたURLと取得実体は1920×1608だった。先に取得した1920px版とバイト単位のハッシュも一致する。APIの寸法値を取得画像の実寸として記録しない。画像は調査用キャッシュにのみ置き、Gitや配布物には追加しない。

公開DBのE87Dは候補0件・`requires_source_evidence`・`unreviewed`のままである。原典への到達は進んだが、PUAフォント欠落の解消やKAGE対応の確定を意味しない。
