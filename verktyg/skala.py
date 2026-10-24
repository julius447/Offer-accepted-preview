#!/usr/bin/env python3
"""Läser varje längd i styles.css och säger vilka som ligger utanför skalan.

    python3 verktyg/skala.py            # bara de som bryter
    python3 verktyg/skala.py --alla     # varje längd, med rad

Huset har EN avståndsskala (2 / 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64), EN
storleksskala för komponenters egna mått (16 / 20 / 24 / 32 / 44 / 48) och
FYRA radier (10 / 14 / 20 / 28). `gemensamt/system.css` rad 19 till 42.
"Ett värde utanför skalan är en bugg, inte en smaksak" (FALLOR.md).

UPPMÄTT 2026-10-24, samma mätare på filen före skalpasset: 51 deklarationer
utanför skalan, med 28 distinkta värden (1, 3, 6, 7, 9, 11, 12, 12.5, 13,
13.5, 14, 14.5, 16, 18, 19, 21, 23, 26, 27, 30, 31, 34, 36, 40, 42, 72, 86,
440). Efter: 0. Kör mätaren på en äldre version av filen och den visar dem
igen, så provet kan falla.

UNDANTAGEN ÄR NAMNGIVNA OCH FÅ. Står ett tal inte i listan nedan är det
glidning, inte ett beslut. Hårlinjer, skuggor, fokusring och de två aurora-
figurernas egna bredder hör inte till rytmen, och de räknas därför inte.
"""
import pathlib
import re
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent

SPACING = {0, 2, 4, 8, 12, 16, 24, 32, 48, 64}
STORLEK = {16, 20, 24, 32, 44, 48}
RADIE = {10, 14, 20, 28, 999}   # 999 = pillret; 50% star inte i px
TYP = {30, 24, 20, 17, 15, 13, 11}
TILLATNA = SPACING | STORLEK | RADIE

# Egenskaper vars px-värden INTE hör till rytmen. Varje rad är ett beslut.
FRITT = {
    "border": "harlinjer, 1 px",
    "border-top": "harlinjer, 1 px",
    "border-width": "harlinjer",
    "box-shadow": "skuggans utbredning ar ingen rytm",
    "outline": "fokusringen ar 3 px, WCAG 2.4.11",
    "outline-offset": "fokusringens avstand till kanten",
    "text-underline-offset": "typografisk detalj, 3 px",
    "stroke-width": "svg-penna",
    "width": "",       # hanteras per selektor nedan
    "height": "",
    "max-width": "",
    "min-width": "",
    "min-height": "",
    "left": "", "top": "", "right": "", "bottom": "",
    "margin-left": "", "margin-top": "",
    "backdrop-filter": "blur",
    "-webkit-backdrop-filter": "blur",
    "filter": "blur",
}

# Selektorer där ett mått är komponentens eget och har sitt skäl skrivet.
UNDANTAG = {
    ".oa__card": {540: "kortets max-width, layoutens enda fasta bredd"},
    ".oa__aurora--top": {200: "aurorafigurens egen bredd", 400: "aurorafigurens egen bredd"},
    ".oa__aurora--bottom": {150: "aurorafigurens egen bredd", 280: "aurorafigurens egen bredd"},
    ".oa__bock svg": {10: "husets eget matt i .o-bock svg"},
    ".oa__step:not(:last-child)::after": {1: "harlinje", 2: "harlinje"},
}


def langder(css):
    """[(rad, selektor, egenskap, px)] för varje px-värde i filen."""
    css = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), css, flags=re.S)
    ut, selektor = [], "?"
    for i, rad in enumerate(css.split("\n"), 1):
        m = re.match(r"\s*([^{}]*?)\s*\{", rad)
        if m and m.group(1).strip():
            selektor = m.group(1).strip()
        for d in re.finditer(r"(^|[;{])\s*([a-zA-Z-]+)\s*:([^;}]*)", rad):
            egenskap, varde = d.group(2), d.group(3)
            if egenskap.startswith("--"):
                continue
            for t in re.finditer(r"(-?\d+(?:\.\d+)?)px", varde):
                ut.append((i, selektor, egenskap, abs(float(t.group(1)))))
    return ut


def bryter(css):
    fel = []
    for rad, sel, egenskap, px in langder(css):
        if egenskap in ("font-size",):
            if px not in TYP:
                fel.append((rad, sel, egenskap, px, "inte en av husets sju typstorlekar"))
            continue
        if egenskap in FRITT and FRITT[egenskap]:
            continue
        for s, tal in UNDANTAG.items():
            if sel.endswith(s) and px in tal:
                break
        else:
            if egenskap in FRITT:            # width/height/left/... utan undantag
                if px not in TILLATNA:
                    fel.append((rad, sel, egenskap, px, "inte pa storleks- eller avstandsskalan"))
                continue
            if px not in TILLATNA:
                fel.append((rad, sel, egenskap, px, "inte pa avstandsskalan"))
    return fel


if __name__ == "__main__":
    css = (HAR / "styles.css").read_text(encoding="utf-8")
    if "--alla" in sys.argv:
        for rad, sel, e, px in langder(css):
            print("%4d  %-44s %-22s %gpx" % (rad, sel[:44], e, px))
        print()
    f = bryter(css)
    for rad, sel, e, px, skal in f:
        print("rad %-4d %-40s %-18s %-7g %s" % (rad, sel[:40], e, px, skal))
    print("%d langder utanfor skalan" % len(f))
    sys.exit(1 if f else 0)
