"""Bundled and content-addressed user fonts, without silent fallback."""
import hashlib
import io
import os
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent
USER_FONTS = Path(os.environ.get("LETTER_MAKER_DATA", str(ROOT.parents[1] / ".local"))) / "fonts"
BUNDLED = {
    "dejavu-sans-bold": ("DejaVu Sans Bold", ROOT / "DejaVuSans-Bold.ttf"),
    "dejavu-sans": ("DejaVu Sans", ROOT / "DejaVuSans.ttf"),
    "dejavu-serif-bold": ("DejaVu Serif Bold", ROOT / "DejaVuSerif-Bold.ttf"),
}


def resolve_font(font_id: str) -> Path:
    if font_id in BUNDLED:
        return BUNDLED[font_id][1]
    if font_id.startswith("user-") and len(font_id) == 69:
        p = USER_FONTS / f"{font_id}.font"
        if p.is_file():
            return p
    raise ValueError("Brakuje fontu projektu. Zaimportuj ponownie ten sam plik TTF/OTF; font nie został podmieniony.")


def font_name(font: TTFont) -> str:
    return font["name"].getDebugName(4) or "Font użytkownika"


def list_fonts():
    fonts = [{"id": k, "name": name, "bundled": True} for k, (name, _) in BUNDLED.items()]
    if USER_FONTS.exists():
        for p in sorted(USER_FONTS.glob("user-*.font")):
            try:
                with TTFont(p) as f:
                    fonts.append({"id": p.stem, "name": font_name(f), "bundled": False})
            except Exception:
                continue
    return fonts


def import_font(data: bytes):
    if len(data) > 10 * 1024 * 1024:
        raise ValueError("Maksymalny rozmiar fontu to 10 MB.")
    if data[:4] not in (b"\x00\x01\x00\x00", b"OTTO", b"true"):
        raise ValueError("Wybierz pojedynczy font TTF lub OTF (bez kolekcji TTC i WOFF).")
    try:
        with TTFont(io.BytesIO(data), lazy=False) as font:
            if font["maxp"].numGlyphs > 40000:
                raise ValueError("Zbyt duża liczba glifów.")
            if not ("glyf" in font or "CFF " in font or "CFF2" in font):
                raise ValueError("Font nie zawiera obsługiwanych obrysów.")
            font.getGlyphSet()
            name = font_name(font)
    except Exception as exc:
        raise ValueError(f"Nieprawidłowy font TTF/OTF: {exc}") from exc
    font_id = "user-" + hashlib.sha256(data).hexdigest()
    USER_FONTS.mkdir(parents=True, exist_ok=True)
    (USER_FONTS / f"{font_id}.font").write_bytes(data)
    return {"id": font_id, "name": name, "bundled": False}
