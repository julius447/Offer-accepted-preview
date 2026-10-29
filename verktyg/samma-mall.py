#!/usr/bin/env python3
"""EN MALL, EN SKILLNAD. Mäter att de fem byggda sidorna är samma markup.

    python3 verktyg/samma-mall.py           # de fem, mot varandra
    python3 verktyg/samma-mall.py --diff    # och varje skillnad rad för rad

ÄGARENS ORD 25 OKTOBER, ORDAGRANT:
    "När jag har gått igenom mallarna ser jag att varenda mall är lite
     annorlunda. (...) Orderbekräftelsen kommer inte att ha olika mallar. Det
     enda är ju tilläggsarbetet, eftersom 'Så här går vi vidare' är
     annorlunda. Det är egentligen den enda skillnaden."

UNDANTAGET FÖLL BORT 29 OKTOBER, och mätningen blev strängare av det.
Ägarordern samma dag: "SÅHÄR GÅR VI VIDARE och alla dess 1/2/3 steg och copy
tar vi bort helt och hållet från alla acceptera mallarna." Fanns ingen
steglista kvar finns inget att undanta, och ägarens egen mening blir sann
UTAN förbehåll: alla fem sidorna är nu samma tecken. Kravet är inte raderat
utan vänt: provet kräver numera att ingen av de fem HAR en steglista.

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
# oaKostnaderKropp och oaForberedKropp kom till 29 oktober. De är data på
# exakt samma sätt som oaRader: laddboxen har sju prissatta rader, batteriet
# nio, elcentralen tre villkorstexter utan pris, service och tillägg ingen
# fold alls. Att de skiljer sig ÄR kontraktet, inte två mallar. Att innehållet
# stämmer provas av verktyg/ordagrant.py och verktyg/talen.py, som läser varje
# sträng och varje tal mot offertrepots egna filer.
DATA_FACK = ["oaTitel", "oaRefEtikett", "oaRefNr", "oaAcceptDatum",
             "oaPaket", "oaTotal", "oaProdRubrik", "oaProdUnder"]
# FACK MED EGEN MARKUP INUTI blankas till sin slutande tagg, inte till nasta.
# DATA_FACK-regexen slutar pa forsta "</", och foldarnas kropp innehaller
# <p> och <ul>: den traffade "</p>" och lamnade listan kvar. Samma losning som
# oaRader och oaIngar redan har, och samma fel de en gang hade.
FACK_MED_MARKUP = [("oaKostnaderKropp", "</div>"), ("oaForberedKropp", "</div>")]


def dela(html):
    """(skelettet utanför stegen, steglistans skelett)."""
    s = re.sub(r"<!-- BYGGD FIL.*?-->\n", "", html, flags=re.S)
    s = re.sub(r"<title>.*?</title>", "<title>DATA</title>", s, flags=re.S)
    s = s.replace(' hidden=""', "")
    for fack in DATA_FACK:
        s = re.sub(r'(id="%s"[^>]*>).*?(</)' % fack, r"\1DATA\2", s, flags=re.S)
    for fack, slut in FACK_MED_MARKUP:
        s = re.sub(r'(id="%s">).*?(%s)' % (fack, re.escape(slut)), r"\1DATA\2", s, flags=re.S)
    s = re.sub(r'(id="oaRader">).*?(</ul>)', r"\1RADER\2", s, flags=re.S)
    s = re.sub(r'(id="oaIngar">).*?(</ul>)', r"\1INGAR\2", s, flags=re.S)
    # STEGLISTAN LYFTES TIDIGARE UT och jämfördes för sig, eftersom tillägget
    # fick ha en egen. Den finns inte längre på någon av de fem (ägarorder 29
    # oktober), så det finns inget att lyfta ut. Returvärdet är kvar som ett
    # par så anroparen inte behöver ändras, och andra halvan bär nu BEVISET på
    # att listan är borta i stället för dess innehåll.
    kvar = re.findall(r'oa__steps|oa__step\b|data-oa-steg', s)
    return s, ("STEGLISTA: %s" % ", ".join(sorted(set(kvar)))) if kvar else "INGEN STEGLISTA"


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

    # 2. STEGEN SKA INTE FINNAS, på någon av de fem.
    #    Kravet är vänt, inte raderat: fram till 29 oktober krävde provet att
    #    exakt tilläggsmallen hade en EGEN steglista. Nu kräver det att ingen
    #    har någon alls. Ett borttaget krav är en kontroll mindre för alltid;
    #    ett vänt krav stoppar återkomsten.
    for mall in MALLAR:
        antal += 1
        if stegen[mall] != "INGEN STEGLISTA":
            fel.append("samma-mall: %s har en steglista igen (%s). Ägarorder 29 okt: "
                       "'SÅHÄR GÅR VI VIDARE och alla dess 1/2/3 steg och copy tar vi "
                       "bort helt och hållet från alla acceptera mallarna.'"
                       % (mall, stegen[mall]))
    skiljer = []
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
