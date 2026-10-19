# Microsoft Store掲載文｜Image Privacy Cleaner｜レビュー準備稿
対象ブランチ: `ui/safe-product-upgrade-20261019`
状態: **文案完成 / 公開未承認 / Store ID・価格の実入力未済**
価格の仮設定: **無料候補（仮）**。正式価格・対応市場は権限のある販売者が承認し、Partner Centerで指定する。

## ja-JP
**製品名（候補）:** Image Privacy Cleaner

**短い説明:**
画像上の隠したい場所をマウスで指定して黒塗りし、対応する画像メタデータを除去したコピーを保存します。

**詳細説明（そのまま編集欄へ転記可能）:**
スクリーンショットや写真を読み込み、画面上で黒塗りしたい範囲を選んで、新しい画像として保存します。画像ごとに領域を指定でき、位置を間違えて一括適用しにくい操作画面を備えています。

・画像を見ながらマウスで黒塗り範囲を指定
・画像ごとの黒塗り領域を保持
・対応メタデータの除去とPNG新規保存

**対応範囲と重要な注意事項:**
画像内の人名、顔、QRコードやすべての個人情報を自動検出する機能はありません。黒塗り後も必ず目視してください。動画・複数フレーム等は対応外です。

**What's new:** 初回提出時は空欄。製品更新の場合のみ新旧の違いを事実確認して記載。

## en-US
**Suggested title:** Image Privacy Cleaner

**Short description:**
Redact selected image areas by dragging over them and save a new copy with supported metadata removed.

**Full description:**
Open screenshots or photos, select areas to black out using the image preview, and export separate copies. Redaction areas are associated with individual images. Supported image metadata is removed as part of the process.

• Draw redaction areas directly on the preview
• Keep redaction regions separate for each image
• Save a new lossless PNG with output checks

**Important limitations:**
No automatic detection of text, faces, QR codes or all personal information. Review every image before sharing. Video and animated or multi-frame inputs are not covered.

**What's new:** Leave blank for the initial submission.

## Partner Center 編集チェック
- 描写の対象は各製品の現行ブランチで**実装が確認できる機能のみ**。未知の機能や完全安全保証を足さない。
- 正式名の重複確認、年齢区分質問票、価格、カテゴリ、地域、検索キーワード、機能欄は提出画面で設定する。価格は購入実績の裏付けがない仮説。
- スクリーンショットは実機撮影5枚。本文に外部URL、HTML、未確認の商標や第三者との提携表現を入れない。
- 最終チェック: ユーザー向けの日本語/英語を実画面と照合。英語UIが未合格なら対応言語を無理に追加しない。
- ソースWindows QA、MSIX、Store Identity、プライバシー・サポート情報、ライセンス承認が揃うまで掲載しない。

公式: https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/add-and-edit-store-listing-info
