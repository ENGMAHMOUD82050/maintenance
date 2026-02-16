# translator.py
from functools import lru_cache

@lru_cache(maxsize=5000)
def to_ar(text: str) -> str:
    """
    Offline EN->AR translation using Argos Translate if available.
    Falls back to original text if translation engine/model not installed.
    """
    if text is None:
        return ""
    s = str(text).strip()
    if not s:
        return ""

    # If the text is already Arabic (simple heuristic), return as-is
    # Arabic Unicode range: \u0600-\u06FF
    if any('\u0600' <= ch <= '\u06FF' for ch in s):
        return s

    try:
        import argostranslate.translate as argos_translate
        # This will work only if EN->AR package is installed
        return argos_translate.translate(s, "en", "ar")
    except Exception:
        # No engine or no model -> do not crash printing
        return s
