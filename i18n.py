from __future__ import annotations

import ctypes
import json
import locale
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

LANGUAGE_ENV = "PRIVACY_WINDOWS_LANGUAGE"
_CONTROLLERS: list["LanguageController"] = []
_PATCHED = False


def _settings_path() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / "PrivacyWindowsTools" / "language.json"
    return Path.home() / ".privacy-windows-tools" / "language.json"


def _saved_language() -> str | None:
    try:
        value = json.loads(_settings_path().read_text(encoding="utf-8")).get("language")
        return value if value in {"en", "ja"} else None
    except Exception:
        return None


def _windows_ui_language() -> str | None:
    if os.name != "nt":
        return None
    try:
        lang_id = int(ctypes.windll.kernel32.GetUserDefaultUILanguage())
        return "ja" if (lang_id & 0x3FF) == 0x11 else "en"
    except Exception:
        return None


def _initial_language() -> str:
    override = os.environ.get(LANGUAGE_ENV, "").strip().lower()
    if override in {"en", "ja"}:
        return override
    saved = _saved_language()
    if saved:
        return saved
    windows_language = _windows_ui_language()
    if windows_language:
        return windows_language
    candidates = [locale.getlocale()[0] or "", os.environ.get("LANG", "")]
    return "ja" if any(value.lower().startswith("ja") for value in candidates) else "en"


_LANGUAGE = _initial_language()

TEXTS: dict[str, tuple[str, str]] = {
    "AI Upload Guard": ("AI Upload Guard", "AIアップロードガード"), "Image Privacy Cleaner": ("Image Privacy Cleaner", "画像プライバシークリーナー"), "Local Document Extractor": ("Local Document Extractor", "ローカル文書抽出"), "Document Extractor": ("Document Extractor", "文書抽出"), "PDF Privacy Toolkit": ("PDF Privacy Toolkit", "PDFプライバシーツールキット"), "Excel / CSV Privacy Cleaner": ("Excel / CSV Privacy Cleaner", "Excel / CSVプライバシークリーナー"), "Privacy Cleaner": ("Privacy Cleaner", "プライバシークリーナー"), "Secure Share Packager": ("Secure Share Packager", "セキュア共有パッケージャー"), "Local Report Maker": ("Local Report Maker", "ローカルレポート作成"), "Folder Privacy Auditor": ("Folder Privacy Auditor", "フォルダプライバシー監査"),
    "AI Upload Guard — Windows": ("AI Upload Guard — Windows", "AIアップロードガード — Windows"), "Image Privacy Cleaner — Windows": ("Image Privacy Cleaner — Windows", "画像プライバシークリーナー — Windows"), "Local Document Extractor — Windows": ("Local Document Extractor — Windows", "ローカル文書抽出 — Windows"), "PDF Privacy Toolkit — Windows": ("PDF Privacy Toolkit — Windows", "PDFプライバシーツールキット — Windows"), "Excel / CSV Privacy Cleaner — Windows": ("Excel / CSV Privacy Cleaner — Windows", "Excel / CSVプライバシークリーナー — Windows"), "Secure Share Packager — Windows": ("Secure Share Packager — Windows", "セキュア共有パッケージャー — Windows"), "Local Report Maker — Windows": ("Local Report Maker — Windows", "ローカルレポート作成 — Windows"), "Folder Privacy Auditor — Windows": ("Folder Privacy Auditor — Windows", "フォルダプライバシー監査 — Windows"), "Privacy Complete Suite — Windows": ("Privacy Complete Suite — Windows", "Privacy Complete Suite — Windows"), "AI Safety Pack — Windows": ("AI Safety Pack — Windows", "AI Safety Pack — Windows"), "Document Privacy Pack — Windows": ("Document Privacy Pack — Windows", "Document Privacy Pack — Windows"), "Business Pack — Windows": ("Business Pack — Windows", "Business Pack — Windows"),
    "Local pre-flight inspection before sending files to AI/external services": ("Local pre-flight inspection before sending files to AI/external services", "AIや外部サービスへ送信する前に、ローカルでファイルを事前点検します"), "Strip EXIF/GPS metadata and optionally black-redact regions. Processing stays local.": ("Strip EXIF/GPS metadata and optionally black-redact regions. Processing stays local.", "EXIF/GPSメタデータを削除し、必要に応じて黒塗りします。処理はローカルで完結します。"), "Extract only the text/tables you need before sharing with AI or third parties.": ("Extract only the text/tables you need before sharing with AI or third parties.", "AIや第三者へ共有する前に、必要なテキストや表だけをローカルで抽出します。"), "Merge, split, reorder/delete pages, remove document/XMP metadata, and optionally AES-256-R5 password-protect PDFs locally.": ("Merge, split, reorder/delete pages, remove document/XMP metadata, and optionally AES-256-R5 password-protect PDFs locally.", "PDFの結合・分割・ページ並べ替え/削除・文書/XMPメタデータ削除・AES-256-R5パスワード保護をローカルで行います。"), "Create a safer copy locally. Original files are never overwritten.": ("Create a safer copy locally. Original files are never overwritten.", "ローカルで安全化したコピーを作成します。元ファイルは上書きしません。"), "Create a local ZIP + manifest + SHA256 before sharing files externally.": ("Create a local ZIP + manifest + SHA256 before sharing files externally.", "外部共有前に、ローカルでZIP・マニフェスト・SHA256を作成します。"), "CSV/XLSXからローカルで業務PDFレポートを作成します。外部アップロードは行いません。": ("Create business PDF reports locally from CSV/XLSX. No external upload is performed.", "CSV/XLSXからローカルで業務PDFレポートを作成します。外部アップロードは行いません。"), "Audit a folder locally for data-bearing files, PII candidates, hidden files and duplicates.": ("Audit a folder locally for data-bearing files, PII candidates, hidden files and duplicates.", "フォルダをローカル監査し、データファイル・個人情報候補・隠しファイル・重複を確認します。"),
    "Add files": ("Add files", "ファイルを追加"), "Scan": ("Scan", "スキャン"), "Create safer copies": ("Create safer copies", "安全化コピーを作成"), "Add images": ("Add images", "画像を追加"), "Inspect": ("Inspect", "確認"), "Clean & export": ("Clean & export", "クリーニングして出力"), "Black-redaction rectangles (x,y,width,height; ...):": ("Black-redaction rectangles (x,y,width,height; ...):", "黒塗り範囲 (x,y,幅,高さ; ...):"), "Flatten output to metadata-free PNG": ("Flatten output to metadata-free PNG", "メタデータを除去したPNGへフラット化"), "Add documents": ("Add documents", "文書を追加"), "Extract all": ("Extract all", "すべて抽出"), "Export Markdown": ("Export Markdown", "Markdownを出力"), "Optional keyword filter (comma separated):": ("Optional keyword filter (comma separated):", "任意のキーワードフィルター（カンマ区切り）:"),
    "Add PDFs": ("Add PDFs", "PDFを追加"), "Sanitize first": ("Sanitize first", "先頭PDFを安全化"), "Split first": ("Split first", "先頭PDFを分割"), "Merge all": ("Merge all", "すべて結合"), "Pages to keep/order for Sanitize (example: 1,3-5,2; blank = all):": ("Pages to keep/order for Sanitize (example: 1,3-5,2; blank = all):", "安全化で残す/並べるページ（例: 1,3-5,2、空欄=すべて）:"), "Optional output password (AES-256-R5):": ("Optional output password (AES-256-R5):", "任意の出力パスワード (AES-256-R5):"),
    "Choose CSV/XLSX": ("Choose CSV/XLSX", "CSV/XLSXを選択"), "Export safer copy": ("Export safer copy", "安全化コピーを出力"), "Columns to process (comma separated; blank = all columns):": ("Columns to process (comma separated; blank = all columns):", "処理する列（カンマ区切り、空欄=全列）:"), "Mode: mask / pseudonymize / drop": ("Mode: mask / pseudonymize / drop", "モード: mask / pseudonymize / drop"), "Pseudonym salt (keep stable if you need consistent IDs):": ("Pseudonym salt (keep stable if you need consistent IDs):", "仮名化ソルト（同じID対応が必要なら固定してください）:"), "Remove hidden worksheets (XLSX)": ("Remove hidden worksheets (XLSX)", "非表示ワークシートを削除 (XLSX)"), "Remove cell comments (XLSX)": ("Remove cell comments (XLSX)", "セルコメントを削除 (XLSX)"),
    "Build package": ("Build package", "パッケージを作成"), "Sanitize supported PDF/images": ("Sanitize supported PDF/images", "対応PDF/画像を安全化"), "Preview summary": ("Preview summary", "概要をプレビュー"), "Generate PDF": ("Generate PDF", "PDFを生成"), "Choose folder": ("Choose folder", "フォルダを選択"), "Run audit": ("Run audit", "監査を実行"), "Export CSV + JSON": ("Export CSV + JSON", "CSV + JSONを出力"),
    "Ready": ("Ready", "準備完了"), "Not installed / build missing": ("Not installed / build missing", "未インストール / ビルドなし"), "Open": ("Open", "開く"), "Launch error": ("Launch error", "起動エラー"), "Bundle error": ("Bundle error", "Bundleエラー"), "SALES RELEASE": ("SALES RELEASE", "販売リリース"), "DEVELOPMENT / NOT FOR SALE": ("DEVELOPMENT / NOT FOR SALE", "開発用 / 販売禁止"), "Complete Windows privacy toolkit / 全製品ランチャー": ("Complete Windows privacy toolkit", "Windowsプライバシーツール全製品ランチャー"), "Windows local tools / ローカル実行": ("Windows local tools", "Windowsローカルツール"),
    "Select files": ("Select files", "ファイルを選択"), "Select images": ("Select images", "画像を選択"), "Select documents": ("Select documents", "文書を選択"), "Select PDFs": ("Select PDFs", "PDFを選択"), "Choose output folder": ("Choose output folder", "出力フォルダを選択"), "Choose split output folder": ("Choose split output folder", "分割出力フォルダを選択"), "Choose CSV or XLSX": ("Choose CSV or XLSX", "CSVまたはXLSXを選択"), "Choose folder to audit": ("Choose folder to audit", "監査するフォルダを選択"), "Select files to package": ("Select files to package", "パッケージするファイルを選択"), "Save extracted Markdown": ("Save extracted Markdown", "抽出Markdownを保存"), "Report base name": ("Report base name", "レポートの基本名"),
    "Unsupported": ("Unsupported", "未対応"), "Invalid rectangles": ("Invalid rectangles", "無効な黒塗り範囲"), "Select one or more files first.": ("Select one or more files first.", "先に1つ以上のファイルを選択してください。"), "Select files first.": ("Select files first.", "先にファイルを選択してください。"), "Add images first.": ("Add images first.", "先に画像を追加してください。"), "Add documents first.": ("Add documents first.", "先に文書を追加してください。"), "Add a PDF first.": ("Add a PDF first.", "先にPDFを追加してください。"), "Add at least two PDFs to merge.": ("Add at least two PDFs to merge.", "結合するPDFを2つ以上追加してください。"), "Choose a file first.": ("Choose a file first.", "先にファイルを選択してください。"), "Choose a data file first.": ("Choose a data file first.", "先にデータファイルを選択してください。"), "Choose a folder first.": ("Choose a folder first.", "先にフォルダを選択してください。"), "Add files first.": ("Add files first.", "先にファイルを追加してください。"), "Mode must be mask, pseudonymize, or drop.": ("Mode must be mask, pseudonymize, or drop.", "モードは mask、pseudonymize、drop のいずれかにしてください。"), "Only CSV and XLSX are supported.": ("Only CSV and XLSX are supported.", "CSVとXLSXのみ対応しています。"),
    "Data files": ("Data files", "データファイル"), "Data": ("Data", "データ"), "Output": ("Output", "出力"), "Text": ("Text", "テキスト"), "Excel": ("Excel", "Excel"), "Markdown": ("Markdown", "Markdown"), "PDF": ("PDF", "PDF"), "CSV": ("CSV", "CSV"), "ZIP": ("ZIP", "ZIP"),
}

PHRASES: tuple[tuple[str, str], ...] = (
    ("Unsupported or undecodable text encoding", "未対応またはデコード不能な文字コード"), ("Unsupported or undecodable CSV encoding", "未対応またはデコード不能なCSV文字コード"), ("Decoded text contains NUL bytes and appears binary", "テキストにNULバイトが含まれ、バイナリデータの可能性があります"), ("Decoded text contains too many control characters and appears binary", "制御文字が多すぎるため、バイナリデータの可能性があります"), ("supported encodings", "対応文字コード"), ("invalid/corrupt", "無効/破損"), ("parser failure", "解析失敗"), ("file access failure", "ファイルアクセス失敗"), ("unsupported/unknown extension", "未対応/不明な拡張子"), ("file exceeds 200 MB limit", "ファイルが200MBの上限を超えています"), ("executable/active-content type", "実行可能/アクティブコンテンツ形式"), ("email address candidate", "メールアドレス候補"), ("phone number candidate", "電話番号候補"), ("long numeric identifier candidate", "長い数値識別子候補"), ("macro content detected", "マクロ内容を検出"), ("external links detected", "外部リンクを検出"), ("comments detected", "コメントを検出"), ("metadata present", "メタデータあり"), ("Encrypted PDF", "暗号化PDF"), ("encrypted PDF", "暗号化PDF"), ("Page out of range", "ページ範囲外"), ("Unsupported image", "未対応の画像"), ("Unsupported document", "未対応の文書"), ("Unsupported format", "未対応形式"), ("Blocked executable/active-content file", "実行可能/アクティブコンテンツのためブロックしたファイル"), ("Symbolic links are not packaged", "シンボリックリンクはパッケージしません"), ("Not a file", "ファイルではありません"), ("Refusing to overwrite the original file", "元ファイルの上書きを拒否しました"), ("Refusing to overwrite the original PDF", "元PDFの上書きを拒否しました"), ("Refusing to overwrite the original image", "元画像の上書きを拒否しました"), ("Refusing to overwrite an input file with the output ZIP", "出力ZIPで入力ファイルを上書きすることを拒否しました"), ("Refusing to overwrite an input document", "入力文書の上書きを拒否しました"), ("Duplicate CSV header(s)", "重複したCSVヘッダー"), ("Duplicate worksheet", "重複したワークシート"), ("contains a blank header", "空のヘッダーが含まれています"), ("more fields than the header", "ヘッダーより多いフィールドがあります"), ("Requested column(s) not found", "指定した列が見つかりません"), ("missing requested column(s)", "指定した列がありません"), ("Refusing to drop every", "すべての列を削除する操作を拒否しました:"), ("no flagged issue in supported checks", "対応チェックでは問題候補なし"), ("no EXIF/GPS/ICC flags", "EXIF/GPS/ICCの検出なし"), ("manual review required", "手動確認が必要"), ("hash skipped", "ハッシュを省略"), ("hash failed", "ハッシュ失敗"), ("duplicate content", "重複内容"), ("hidden file/path", "隠しファイル/パス"), ("data-bearing file type", "データを含む可能性のある形式"), ("Created", "作成"), ("Exported", "出力"), ("Saved", "保存"), ("SAVED", "保存"), ("REJECTED", "拒否"), ("WARNING", "警告"), ("ACCEPTED", "受付"), ("BLOCKED", "ブロック"), ("ERROR", "エラー"), ("Folder:", "フォルダ:"), ("Files:", "ファイル数:"), ("flagged:", "要確認:"), ("Rows=", "行数="), ("Columns=", "列数="), ("missing=", "欠損="),
)


def get_language() -> str:
    return _LANGUAGE


def translate(text: object) -> object:
    if not isinstance(text, str):
        return text
    exact = TEXTS.get(text)
    if exact:
        return exact[1] if _LANGUAGE == "ja" else exact[0]
    if _LANGUAGE != "ja":
        return text
    translated = text
    for english, japanese in PHRASES:
        translated = translated.replace(english, japanese)
    return translated


def set_language(language: str) -> None:
    global _LANGUAGE
    if language not in {"en", "ja"}:
        raise ValueError("language must be 'en' or 'ja'")
    _LANGUAGE = language
    try:
        path = _settings_path(); path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps({"language": language}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
    for controller in tuple(_CONTROLLERS):
        controller.refresh()


def _patch_runtime_text() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True
    original_insert = tk.Listbox.insert
    def localized_insert(self, index, *elements): return original_insert(self, index, *(translate(value) for value in elements))
    tk.Listbox.insert = localized_insert  # type: ignore[assignment]
    for name in ("showinfo", "showwarning", "showerror", "askyesno", "askokcancel", "askretrycancel"):
        original = getattr(messagebox, name, None)
        if original is None: continue
        def make_message_wrapper(func):
            def wrapper(title, message, *args, **kwargs): return func(translate(title), translate(message), *args, **kwargs)
            return wrapper
        setattr(messagebox, name, make_message_wrapper(original))
    for name in ("askopenfilename", "askopenfilenames", "asksaveasfilename", "askdirectory"):
        original = getattr(filedialog, name, None)
        if original is None: continue
        def make_dialog_wrapper(func):
            def wrapper(*args, **kwargs):
                if "title" in kwargs: kwargs["title"] = translate(kwargs["title"])
                if "filetypes" in kwargs: kwargs["filetypes"] = [(translate(label), pattern) for label, pattern in kwargs["filetypes"]]
                return func(*args, **kwargs)
            return wrapper
        setattr(filedialog, name, make_dialog_wrapper(original))


class LanguageController:
    def __init__(self, root: tk.Misc):
        self.root = root; self.original_title = root.title() if hasattr(root, "title") else ""; self._snapshot(root)
        existing = list(root.winfo_children())
        frame = tk.Frame(root, padx=12, pady=5)
        if existing: frame.pack(fill="x", before=existing[0])
        else: frame.pack(fill="x")
        tk.Label(frame, text="Language / 言語").pack(side="right", padx=(0,8))
        self.toggle_button = tk.Button(frame, width=10, command=self.toggle); self.toggle_button.pack(side="right")
        _CONTROLLERS.append(self); self.refresh()
    def _snapshot(self, widget: tk.Misc) -> None:
        try: setattr(widget, "_i18n_original_text", widget.cget("text"))
        except Exception: pass
        for child in widget.winfo_children(): self._snapshot(child)
    def _refresh_widget(self, widget: tk.Misc) -> None:
        if widget is not getattr(self, "toggle_button", None):
            original = getattr(widget, "_i18n_original_text", None)
            if original is not None:
                try: widget.configure(text=translate(original))
                except Exception: pass
        for child in widget.winfo_children(): self._refresh_widget(child)
    def refresh(self) -> None:
        if hasattr(self.root, "title"): self.root.title(translate(self.original_title))
        self._refresh_widget(self.root); self.toggle_button.configure(text="English" if _LANGUAGE == "ja" else "日本語")
    def toggle(self) -> None: set_language("en" if _LANGUAGE == "ja" else "ja")


def install_bilingual_ui(root: tk.Misc) -> LanguageController:
    _patch_runtime_text(); return LanguageController(root)
