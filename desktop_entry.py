from __future__ import annotations
import sys
import i18n
from language_standard import apply_language_standard
apply_language_standard(i18n, "image-privacy-cleaner")
if __name__ == "__main__":
    if "--self-test" in sys.argv:
        import smoke_test  # noqa: F401 - importing runs the fail-closed acceptance suite
        raise SystemExit(0)

    from windows_app import main

    main()
