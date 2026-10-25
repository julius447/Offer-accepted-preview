#!/usr/bin/env python3
"""EN MALL, EN SKILLNAD. Mäter att de fem byggda sidorna är samma markup.

    python3 verktyg/samma-mall.py           # de fem, mot varandra
    python3 verktyg/samma-mall.py --diff    # och varje skillnad rad för rad

ÄGARENS ORD 25 OKTOBER, ORDAGRANT:
    "När jag har gått igenom mallarna ser jag att varenda mall är lite
     annorlunda. (...) Orderbekräftelsen kommer inte att ha olika mallar. Det
     enda är ju tilläggsarbetet, eftersom 'Så här går vi vidare' är
     annorlunda. Det är egentligen den enda skillnaden."

Det är ett PÅSTÅENDE OM MARKUP, och det går därför att mäta i stället för att
försäkra. Mätningen tar varje byggd sida, blankar det som är DATA och jämför
resten tecken för tecken:

  * byggets egen huvudkommentar (namnger källfilen) tas bort
  * <title> blankas: tilläggsmallen byter flikrubriken ur kontraktet
  * hidden="" tas bort. Att produktraden syns på laddboxen och inte på
    servicen är kontraktets fält order.rubrik, inte två mallar
  * innehållet i de namngivna datafacken blankas (DATA_FACK nedan)
  * radlistan och ingår-listan ersätts av en markör: deras LÄNGD är ordern
  * steglistan lyfts ut och jämförs för sig, med sin egen text blankad

VAD SOM AVSIKTLIGT INTE BLANKAS, och varför det är själva poängen:
`oaFin`, `oaKvittoNot` och `oaVillkorKropp` står kvar med sin text. Det var
där mallarna drog isär: finstilten sa "(ROT)" på elcentralen, "(Grön teknik)"
på batteriet och "(Grön teknik och ROT)" på laddboxen, alltså tre lydelser på
fem sidor. Efter ägarens 25 oktober säger alla fem samma mening, och då ska
den jämföras, inte blankas bort.

MÄTT FÖRE PASSET 25 OKTOBER: samma mätare på de sidorna gav fem olika
skelett. Skillnaderna var pottmärkningarna på raderna (laddbox och tillägg),
noten under raderna (laddbox), specerna under ingår-punkterna (service) och
tre olika finstiltsmeningar. Efter: ett skelett för alla fem.
"""
import difflib
import pathlib
import re
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]

# Facken kontraktet fyller med den här orderns egna värden. Ett fack till
# här är ett beslut: det säger "den här texten FÅR skilja mellan fallen".
DATA_FACK = ["oaTitel", "oaRefEtikett", "oaRefNr", "oaAcceptDatum",
             "oaPaket", "oaTotal", "oaProdRubrik", "oaProdUnder"]


def dela(html):
    """(skelettet utanför stegen, steglistans skelett)."""
    s = re.sub(r"<!-- BYGGD FIL.*?-->\n", "", html, flags=re.S)
    s = re.sub(r"<title>.*?</title>", "<title>DATA</title>", s, flags=re.S)
    s = s.replace(' hidden=""', "")
    for fack in DATA_FACK:
        s = re.sub(r'(id="%s"[^>]*>).*?(</)' % fack, r"\1DATA\2", s, flags=re.S)
    s = re.sub(r'(id="oaRader">).*?(</ul>)', r"\1RADER\2", s, flags=re.S)
    s = re.sub(r'(id="oaIngar">).*?(</ul>)', r"\1INGAR\2", s, flags=re.S)
    m = re.search(r'<ol class="oa__steps" id="oaSteps">.*?</ol>', s, flags=re.S)
    if not m:
        return s, "INGEN STEGLISTA"
    steg = re.sub(r'(data-oa-steg="\d+">).*?(</span>)', r"\1DATA\2", m.group(0), flags=re.S)
    steg = re.sub(r'(data-oa-steg-under="\d+">).*?(</small>)', r"\1DATA\2", steg, flags=re.S)
    return s[:m.start()] + "STEGLISTAN" + s[m.end():], steg


def kor(fall=None, tyst=False):
    """(antal kontroller, [fel], vilka mallars steg som skiljer sig)."""
    fall = fall or (HAR / "fall")
    skelett, stegen, fel, antal = {}, {}, [], 0
    saknas = [m for m in MALLAR if not (fall / (m + ".html")).exists()]
    if saknas:
        return 0, ["samma-mall: %s saknas i %s, kör python3 bygg.py" % (saknas, fall)], []
    for mall in MALLAR:
        skelett[mall], stegen[mall] = dela((fall / (mall + ".html")).read_text(encoding="utf-8"))

    # 1. UTANFÖR STEGEN: alla fem ska vara samma tecken.
    bas = MALLAR[0]
    for mall in MALLAR[1:]:
        antal += 1
        if skelett[mall] != skelett[bas]:
            rader = [l for l in difflib.unified_diff(
                skelett[bas].split("\n"), skelett[mall].split("\n"),
                bas, mall, lineterm="", n=0)
                if l[:1] in "+-" and l[:3] not in ("+++", "---")]
            fel.append("samma-mall: %s och %s har olika markup utanför 'Så här går vi "
                       "vidare'. %d rader skiljer, första: %s. Ägaren 25 okt: "
                       "orderbekräftelsen har inte olika mallar."
                       % (bas, mall, len(rader), " / ".join(r.strip()[:90] for r in rader[:2])))

    # 2. STEGEN: exakt tilläggsmallen får skilja sig, och den SKA göra det.
    #    Ett positivt påstående åt båda håll: slutar tillägget byta sin
    #    steglista är det lika fel som att en annan mall börjar byta sin.
    skiljer = sorted(m for m in MALLAR if stegen[m] != stegen[MALLAR[0]])
    antal += 1
    if skiljer != ["tillagg"]:
        fel.append("samma-mall: steglistan skiljer sig på %s, väntade exakt ['tillagg']. "
                   "Ägaren 25 okt: 'Det enda är ju tilläggsarbetet, eftersom Så här går vi "
                   "vidare är annorlunda. Det är egentligen den enda skillnaden.'" % skiljer)
    antal += 1
    if stegen["tillagg"].count("<li") != 2:
        fel.append("samma-mall: tilläggets steglista har %d steg, väntade 2. Steg 3 lovar "
                   "'på avtalad tid' till en kund vars elektriker redan står i hallen."
                   % stegen["tillagg"].count("<li"))
    if not tyst:
        print("%d mallar, skelettet utanför stegen: %s"
              % (len(MALLAR), "ETT" if len({skelett[m] for m in MALLAR}) == 1 else "FLERA"))
        print("steglistan skiljer sig på: %s" % (skiljer or "ingen"))
        if "--diff" in sys.argv:
            for mall in MALLAR[1:]:
                for l in difflib.unified_diff(skelett[MALLAR[0]].split("\n"),
                                              skelett[mall].split("\n"),
                                              MALLAR[0], mall, lineterm="", n=0):
                    print("  " + l[:200])
            for l in difflib.unified_diff(stegen[MALLAR[0]].split("\n"),
                                          stegen["tillagg"].split("\n"),
                                          "steg " + MALLAR[0], "steg tillagg", lineterm="", n=0):
                print("  " + l[:200])
    return antal, fel, skiljer


if __name__ == "__main__":
    n, f, _ = kor()
    print("\n%d kontroller" % n)
    for rad in f:
        print("  * " + rad)
    sys.exit(1 if f else 0)
