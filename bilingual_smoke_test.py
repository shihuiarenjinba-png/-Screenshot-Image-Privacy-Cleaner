import i18n

original = getattr(i18n, "get_language", lambda: getattr(i18n, "_LANGUAGE", "en"))()
try:
    i18n.set_language("ja")
    assert i18n.translate("Add images") == "画像を追加"
    assert i18n.translate("Clean & export") == "クリーニングして出力"
    i18n.set_language("en")
    assert i18n.translate("Add images") == "Add images"
    assert i18n.translate("Clean & export") == "Clean & export"
finally:
    i18n.set_language(original)

print("Image Privacy Cleaner bilingual UI smoke test: OK")
