#!/usr/bin/env python3
"""Tar bort kommentarerna ur det som LEVERERAS, aldrig ur källan.

KOPIERAD, INTE SKRIVEN HÄR. Källa:
    laddboxoffert/gemensamt/verktyg/strippa.py @5545c6b
Två rader skiljer: ROT pekar ett steg upp i stället för tre, och main()
mäter det här repots egna filer. Scannerna och de tio falsifieringarna är
ORÖRDA med flit — de är bevisade där, och en omskrivning här hade varit en
andra sanning om samma sak. Ändras de i offertrepot ska den här filen
kopieras om, inte lappas.

    python3 gemensamt/verktyg/strippa.py            # mät vad som skulle falla bort
    python3 gemensamt/verktyg/strippa.py --prov     # falsifiera stripparna

VARFÖR FILEN FINNS. Ägarbeslut 31 oktober 2026, ordagrant:

    Kund ska inte se interna kommenterar. Kom ihåg att detta repo bara har
    designen. Så ska inte vara några konstigheter då utvecklarna kommer att ta
    mallarna och all dokumentation och sedan implementera det i CRM, Supabase
    och liknande. Så kommentarerna borde försvinna.

Uppmätt samma dag, på det som kunden faktiskt laddar ner:

    html   13 filer  1 327 805 byte  varav   281 019 kommentar  21,2 %
    css    14 filer  1 966 627 byte  varav 1 189 888 kommentar  60,5 %
    js     28 filer    554 996 byte  varav   255 179 kommentar  46,0 %
    ───────────────────────────────────────────────────────────────────
    allt   55 filer  3 869 436 byte  varav 1 761 086 kommentar  45,5 %

Sista raden är mätt på exakt de filer `publicera.py` kopierar, listan läst ur
`publicera.py` självt. Och **955 förekomster av interna ord ligger bara inne i
kommentarerna**: `agaren`/`ägaren` 527, `AGARE` 112, `orakel` 91, `FALLOR` 59,
`defekt` 54, `GAP` 47, `bugg` 23, `prislista` 16, `Rasmus` 13, `AGARFRAGA` 11,
`Felix` 2. Alltså citerade ägarbeslut, namngivna personer, vår interna
prislista och våra egna defektdiskussioner.

**1,76 MB av 3,87 MB var anteckningar till oss själva.** Repot
`julius447/Laddboxofferten` är publikt, så vem som helst kunde läsa dem med Visa
källkod. Den värsta togs bort 27 oktober: den citerade en intern prislista och
två Ampy-priser som sa olika om samma elcentral.

**KÄLLAN RÖRS INTE.** `offerter/*/body.html`, `offert.py`, `skript.js`,
`stil.css` och `gemensamt/` behåller varje kommentar. De är projektets dyrast
byggda tillgång: de säger varför varje tal är som det är, vilket beslut som
gäller och vilken mätning som avgjorde saken. Utvecklaren läser dem i repot,
vilket är precis vad ägaren beskriver att han kommer att göra.

VARFÖR DET INTE GÅR MED ETT REGULJÄRT UTTRYCK. Mätt innan den här filen skrevs:
**18 regexliteraler** i de levererade js-filerna och sex mallsträngar. Ett
mönster som tar `//` till radslut äter in i `/[^/\\n\\\\]+/g`, och ett som tar
`/* ... */` kan börja inne i en teckenklass. Därför scannar stripparna tecken
för tecken och vet när de står i en sträng, en mallsträng eller en regex.

HUR DET BEVISAS. Att en fil blev mindre bevisar ingenting om att den fungerar.
Beviset är tredelat:
  1. `--prov` kör falsifieringar: varje strippare matas med kod där en
     kommentarsekvens står inne i en sträng, en regex och en mallsträng, och
     måste lämna den orörd.
  2. `gemensamt/verktyg/ekvivalens.py` mäter en byggd sida före och efter. En
     borttagen kommentar får inte flytta en enda pixel.
  3. `laddfel.py` fångar fel som kastas under laddning, alltså en js-fil som
     slutat parsa.
"""
import pathlib
import re
import sys

ROT = pathlib.Path(__file__).resolve().parent.parent


def strip_css(t):
    """/* ... */ utanför strängar. CSS har inga radkommentarer."""
    ut = []
    i, n = 0, len(t)
    strang = None
    while i < n:
        c = t[i]
        if strang:
            ut.append(c)
            if c == "\\" and i + 1 < n:
                ut.append(t[i + 1]); i += 2; continue
            if c == strang:
                strang = None
            i += 1
            continue
        if c in "\"'":
            strang = c; ut.append(c); i += 1; continue
        if c == "/" and i + 1 < n and t[i + 1] == "*":
            j = t.find("*/", i + 2)
            i = n if j < 0 else j + 2
            continue
        ut.append(c); i += 1
    return "".join(ut)


# Ett "/" startar en REGEX och inte en division när det föregås av något som
# inte kan avsluta ett uttryck. Listan är den vedertagna heuristiken; den är
# inte en fullständig parser, och därför provar --prov den mot riktiga fall.
_EJ_FORE_REGEX = set(")]}") | set("0123456789")
_ORD_FORE_DIVISION = {"return", "typeof", "instanceof", "in", "of", "new",
                      "delete", "void", "throw", "case", "do", "else", "yield"}


def _foregaende(ut):
    """Sista betydelsebärande tecknet och ordet före det."""
    i = len(ut) - 1
    while i >= 0 and ut[i] in " \t\r\n":
        i -= 1
    if i < 0:
        return "", ""
    c = ut[i]
    j = i
    while j >= 0 and (ut[j].isalnum() or ut[j] in "_$"):
        j -= 1
    return c, "".join(ut[j + 1:i + 1])


def strip_js(t):
    """// och /* ... */ utanför strängar, mallsträngar och regexliteraler."""
    ut = []
    i, n = 0, len(t)
    while i < n:
        c = t[i]
        # strängar
        if c in "\"'":
            ut.append(c); i += 1
            while i < n:
                ut.append(t[i])
                if t[i] == "\\" and i + 1 < n:
                    ut.append(t[i + 1]); i += 2; continue
                if t[i] == c:
                    i += 1; break
                i += 1
            continue
        # mallsträng, med ${ } som kan bära vad som helst
        if c == "`":
            ut.append(c); i += 1
            djup = 0
            while i < n:
                if t[i] == "\\" and i + 1 < n:
                    ut.append(t[i]); ut.append(t[i + 1]); i += 2; continue
                if t[i] == "$" and i + 1 < n and t[i + 1] == "{":
                    djup += 1; ut.append("${"); i += 2; continue
                if t[i] == "}" and djup:
                    djup -= 1; ut.append("}"); i += 1; continue
                if t[i] == "`" and not djup:
                    ut.append("`"); i += 1; break
                ut.append(t[i]); i += 1
            continue
        if c == "/" and i + 1 < n:
            nasta = t[i + 1]
            if nasta == "/":
                j = t.find("\n", i)
                i = n if j < 0 else j
                continue
            if nasta == "*":
                j = t.find("*/", i + 2)
                i = n if j < 0 else j + 2
                continue
            # regexliteral?
            tecken, ord_ = _foregaende(ut)
            ar_regex = (tecken == "" or
                        (tecken not in _EJ_FORE_REGEX and not (tecken.isalnum() or tecken in "_$")) or
                        ord_ in _ORD_FORE_DIVISION)
            if ar_regex:
                ut.append(c); i += 1
                i_klass = False
                while i < n:
                    ut.append(t[i])
                    if t[i] == "\\" and i + 1 < n:
                        ut.append(t[i + 1]); i += 2; continue
                    if t[i] == "[":
                        i_klass = True
                    elif t[i] == "]":
                        i_klass = False
                    elif t[i] == "/" and not i_klass:
                        i += 1; break
                    elif t[i] == "\n":
                        i += 1; break          # inte en regex ändå
                    i += 1
                while i < n and t[i] in "gimsuyd":
                    ut.append(t[i]); i += 1
                continue
        ut.append(c); i += 1
    return "".join(ut)


def strip_html(t):
    """<!-- ... --> utanför <script> och <style>, vars innehåll stripas som js/css."""
    ut = []
    i, n = 0, len(t)
    while i < n:
        m = re.compile(r"<(script|style)\b[^>]*>", re.I).search(t, i)
        k = t.find("<!--", i)
        if k >= 0 and (m is None or k < m.start()):
            ut.append(t[i:k])
            j = t.find("-->", k + 4)
            i = n if j < 0 else j + 3
            continue
        if m is None:
            ut.append(t[i:]); break
        slut_tagg = "</%s>" % m.group(1).lower()
        e = t.lower().find(slut_tagg, m.end())
        if e < 0:
            ut.append(t[i:]); break
        ut.append(t[i:m.end()])
        inre = t[m.end():e]
        ut.append(strip_js(inre) if m.group(1).lower() == "script" else strip_css(inre))
        ut.append(t[e:e + len(slut_tagg)])
        i = e + len(slut_tagg)
    # tomma rader som kommentarerna lämnade efter sig
    return re.sub(r"\n[ \t]*(?=\n)", "", "".join(ut))


def strip_fil(sokvag, text):
    s = str(sokvag)
    if s.endswith(".css"):
        return re.sub(r"\n[ \t]*(?=\n)", "", strip_css(text))
    if s.endswith(".js"):
        return re.sub(r"\n[ \t]*(?=\n)", "", strip_js(text))
    if s.endswith(".html"):
        return strip_html(text)
    return text


# ----------------------------------------------------------------- falsifiering
PROV = [
    ("js: // inne i en sträng", strip_js,
     'var u = "https://ampy.se/x"; // bort\n', 'var u = "https://ampy.se/x"; \n'),
    ("js: /* inne i en sträng", strip_js,
     "var s = '/* inte en kommentar */'; /* bort */\n", "var s = '/* inte en kommentar */'; \n"),
    ("js: regexliteral med snedstreck", strip_js,
     'var r = /a\\/b/g; // bort\n', 'var r = /a\\/b/g; \n'),
    ("js: regex med // i teckenklass", strip_js,
     'var r = /[/*]+/; // bort\n', 'var r = /[/*]+/; \n'),
    ("js: mallsträng med //", strip_js,
     'var t = `se //det här`; // bort\n', 'var t = `se //det här`; \n'),
    ("js: mallsträng med uttryck", strip_js,
     'var t = `a${b ? "//x" : "/*y*/"}c`; /* bort */\n', 'var t = `a${b ? "//x" : "/*y*/"}c`; \n'),
    ("js: division ar inte regex", strip_js,
     'var x = a / b; // bort\nvar y = c / d;\n', 'var x = a / b; \nvar y = c / d;\n'),
    ("css: url med snedstreck", strip_css,
     'a{background:url(https://x/y.png)} /* bort */', 'a{background:url(https://x/y.png)} '),
    ("css: content med stjarnkommentar", strip_css,
     'a{content:"/* kvar */"} /* bort */', 'a{content:"/* kvar */"} '),
    ("html: kommentar i script ar js", strip_html,
     '<p>a</p><!-- bort --><script>var u="//x"; // bort\n</script>',
     '<p>a</p><script>var u="//x"; \n</script>'),
]


def prov():
    fel = 0
    for namn, fn, inne, vantat in PROV:
        fick = fn(inne)
        ok = fick == vantat
        if not ok:
            fel += 1
        print("  %-34s %s" % (namn, "ok" if ok else "FEL"))
        if not ok:
            print("     fick   %r" % fick)
            print("     vantat %r" % vantat)
    print("\n  %d av %d prov passerar" % (len(PROV) - fel, len(PROV)))
    return fel


def main():
    if "--prov" in sys.argv:
        sys.exit(1 if prov() else 0)
    tot = kvar = 0
    for f in sorted(ROT.glob("fall/*.html")) + [ROT / "styles.css", ROT / "script.js",
                                                ROT / "index.html"]:
        if not f.exists():
            continue
        t = f.read_text(encoding="utf-8")
        s_ = strip_fil(f, t)
        a, b = len(t.encode()), len(s_.encode())
        tot += a
        kvar += b
        print("  %-26s %7d -> %7d byte, %6d kommentar (%2.0f %%)"
              % (f.relative_to(ROT), a, b, a - b, 100 * (a - b) / a if a else 0))
    print("  %-26s %7d -> %7d byte, %6d kommentar (%2.0f %%)"
          % ("SUMMA", tot, kvar, tot - kvar, 100 * (tot - kvar) / tot if tot else 0))


if __name__ == "__main__":
    main()
