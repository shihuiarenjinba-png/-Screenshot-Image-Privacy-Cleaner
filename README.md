# Screenshot / Image Privacy Cleaner

スクリーンショットや画像をAI・外部会社へ渡す前に、**候補検出 → 人手確認 → 不可逆pixel redaction → metadata除去 → 出力再検査**までをローカルで行う専用Sanitizerとして設計します。

## 最重要方針

OCR・顔検出・QR検出は**候補位置を出す補助**です。検出されなかった領域を「安全」とは判定しません。

特に文字については、低解像度・小さい文字・回転文字・手書き・図表内文字・半透明表示・特殊fontなどでOCR漏れが起こり得ます。そのため販売版では、完全自動のPASS判定ではなくReview workflowを中心にします。

## 想定workflow

1. 入力画像をローカルで読込
2. EXIF / GPS / XMP / comment等のmetadataを監査
3. OCRで文字boxと認識文字をcandidate化
4. 顔 / QR / barcode等をcandidate化
5. email / phone / token / customer ID等のパターン候補を分類
6. GUI上でユーザーがredaction boxを追加・修正・解除
7. 確定box領域を**元pixelから不可逆に置換**
8. 新しいPNG/JPEGへ再エンコードし、元metadataを引き継がない
9. 出力画像へ再度OCR / QR検査を行い、禁止語candidateが残っていればREVIEW
10. Before/After SHA256、redaction box、検査結果をaudit reportへ保存

## Redaction方式

機密文字にはblurだけを標準にしません。blurは視覚的匿名化には使えても、機密文字の完全削除用途には弱いためです。

- **Solid Redaction**: box内pixelを単色へ完全置換。機密文字向け既定。
- **Pixelation**: 顔などの視覚匿名化用。機密文字には非推奨。
- **Blur**: 視覚匿名化用途のみ。Credential/文字削除の安全モードには使用しない。

出力は元画像へoverlayを追加するのではなく、**redaction済みpixelからbrand-new画像を生成**します。

## OCRの役割

OCRは「自動削除エンジン」ではなく候補検出器です。

- candidate confidenceを表示
- confidenceが低い領域を優先レビュー
- OCRで何も検出しなかった画像も自動PASSにしない
- ユーザーが手動boxを追加できる
- 出力再OCRで残存candidateを確認

## Metadata

- EXIF
- GPS
- XMP
- software/comment fields
- orientation等、再エンコード時に必要なものだけ明示的に再生成

metadataを削除してもpixel内の文字は残るため、metadata sanitizationとvisual redactionは別の検査項目としてreportします。

## 販売上の約束

- 「AI/OCRで100%自動匿名化」とは言わない
- 検出漏れの可能性をUI上で隠さない
- Credential文字はsolid redaction + user confirmationを基本にする
- 元画像を上書きしない
- redaction済み新画像とaudit reportを出す

この製品の価値はAI判断の魔法ではなく、**ローカルで候補を早く見つけ、人が確認し、不可逆な出力を作り、処理内容を追跡できること**に置きます。
