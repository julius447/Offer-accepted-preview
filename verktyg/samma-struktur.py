#!/usr/bin/env python3
"""EN MALL: de fem byggda sidornas ELEMENTVAGAR, inte deras innehall.

    python3 verktyg/samma-struktur.py
    python3 verktyg/samma-struktur.py --vagar      # skriv ut skelettet
    python3 verktyg/samma-struktur.py --sjalvprov  # att provet kan falla

AGARENS ORD, ordagrant: "de ar inte likadana som alla bifogade: Gillar de
bifogade mer da det ar samma mall dar innehallet andras. Har namnt detta till
dig sa varfor ar det inte standarden?"

Det ar ett PASTAENDE OM STRUKTUR, och darfor matbart. Provet tar varje byggd
sida, skalar bort allt som ar innehall, och kraver att de fem skeletten ar
IDENTISKA - samma element, samma klasser, samma id, samma nastling, samma
ordning.

VAD SOM SKALAS BORT, och varfor det inte ar en uppmjukning:
  * texten. Ett skelett ar taggar, inte ord.
  * attributvarden utom class och id. hidden, href, style och aria sager vad
    DEN HAR ordern innehaller, inte vilken mall sidan ar byggd ur.
  * INNEHALLET i datafacken (DATA_FACK nedan). Laddboxen har sex radrader och
    elcentralen tre; servicen har atta punkter i "Allt som ingar" och
    tillagget ingen. Att de skiljer sig AR kontraktet. Sjalva FACKET maste
    daremot finnas pa alla fem, pa samma plats, och det provas.
  * svg-innanmate. Figurerna ar dekor och har sina egna matt.

VAD SOM INTE SKALAS BORT: allt annat. En sektion som bara en mall har, ett
element som bytt plats, en fold som bytt niva, en rubrik som forsvunnit pa en
av fem - allt det faller provet.

FORHALLANDET TILL verktyg/samma-mall.py: den jamfor normaliserad MARKUP tecken
for tecken och ar alltsa strangare. Den har sager i stallet VAD som skiljer,
i elementvagar, vilket ar det felmeddelande man kan agera pa. Tva matare pa
samma krav ar inte dubbelarbete nar den ena sager "2 rader skiljer" och den
andra sager "service saknar h3.oa__ingar-rubrik pa niva 2".
"""
import difflib
import pathlib
import re
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]

# Facken vars INNEHALL ar denna orders egna varden. Ett fack till har ar ett
# beslut: det sager "det som ligger har FAR skilja mellan fallen". Samma
# lista och samma skal som samma-mall.py:s DATA_FACK och FACK_MED_MARKUP.
# VARJE FACK MED SIN EGEN SLUTTAGG, och det ar inte en formalitet.
# Forsta versionen tommde facken med en gemensam `</(?:ul|div)>` och
# icke-gradig matchning. Foldkroppen ar en <div> som INNEHALLER en <ul>, sa
# matchningen slutade pa listans `</ul>` och lamnade `<p class="oa__fold-fot">`
# utanfor facket - plus att nastlingsstacken tappade en niva, vilket flyttade
# oaForbered fran niva 2 till niva 1. Resultatet var tre FALSKA roda pa sidor
# som var hela, och ett sjalvprov dar tva av fem mutationer rapporterade den
# baslinjebuggen i stallet for sin egen verkan. Ett matfel, inte ett fynd.
DATA_FACK = [("oaRader", "ul"), ("oaIngar", "ul"),
             ("oaKostnaderKropp", "div"), ("oaForberedKropp", "div"),
             ("oaVillkorKropp", "div")]

# Taggar utan slut, och svg-innanmatet.
TOMMA = {"br", "hr", "img", "input", "link", "meta", "source", "col", "area"}


def skelett(html):
    """[(niva, 'tagg.klass#id')] for allt inne i .oa, utan innehall."""
    s = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    s = re.sub(r"<svg\b.*?</svg>", " ", s, flags=re.S)
    # DATAFACKEN TOMMAS, men facket sjalvt star kvar och provas.
    for fack, tagg in DATA_FACK:
        s = re.sub(r'(id="%s"[^>]*>).*?(</%s>)' % (fack, tagg), r"\1\2", s, flags=re.S)
    i = s.find('class="oa"')
    if i < 0:
        raise SystemExit("hittar ingen .oa i sidan")
    s = s[i:]
    ut, stack = [], []
    for m in re.finditer(r"<(/?)([a-zA-Z][\w-]*)((?:[^>\"']|\"[^\"]*\"|'[^']*')*?)(/?)>", s):
        slut, tagg, attr, sjalv = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if tagg in TOMMA:
            continue
        if slut:
            if stack:
                stack.pop()
            continue
        kl = re.search(r'class="([^"]*)"', attr)
        idd = re.search(r'id="([^"]*)"', attr)
        namn = tagg
        if kl:
            namn += "." + ".".join(sorted(kl.group(1).split()))
        if idd:
            namn += "#" + idd.group(1)
        ut.append((len(stack), namn))
        if not sjalv:
            stack.append(tagg)
    return ut


def rader(sk):
    return ["  " * n + namn for n, namn in sk]


def kor(tyst=False, sidor=None):
    """(antal element i skelettet, fel). prov.py anropar den har."""
    fel = []
    sk = {}
    for mall in MALLAR:
        f = (HAR / "fall" / (mall + ".html"))
        if sidor and mall in sidor:
            sk[mall] = skelett(sidor[mall])
        elif f.exists():
            sk[mall] = skelett(f.read_text(encoding="utf-8"))
        else:
            fel.append("%s: fall/%s.html saknas" % (mall, mall))
    if not sk:
        return 0, fel
    # LADDBOXEN AR MATTSTOCKEN, och det ar ett godtyckligt men SKRIVET val:
    # nagon sida maste vara referens, och felet sager alltid vilka tva som
    # jamfordes, sa riktningen inte kan missforstas.
    ref = "laddbox" if "laddbox" in sk else sorted(sk)[0]
    for mall in sorted(sk):
        if mall == ref:
            continue
        if sk[mall] == sk[ref]:
            continue
        d = [l for l in difflib.unified_diff(rader(sk[ref]), rader(sk[mall]),
                                             ref, mall, lineterm="", n=0)
             if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        fel.append("%s och %s har OLIKA struktur, %d rader skiljer: %s"
                   % (ref, mall, len(d), [x.strip()[:60] for x in d[:4]]))
    return len(sk[ref]), fel


def sjalvprov():
    """Att provet kan falla. Mutationerna gors I MINNET pa en av de fem
    sidorna, sa ett avbrutet sjalvprov inte lamnar repot muterat."""
    bas = {m: (HAR / "fall" / (m + ".html")).read_text(encoding="utf-8")
           for m in MALLAR}
    # BASLINJEN MASTE VARA GRON. Ett sjalvprov pa en trasig baslinje sager
    # bara att nagot ar rott, inte att mutationen gjorde det.
    _, _basfel = kor(tyst=True)
    if _basfel:
        print("  BASLINJEN AR ROD, sjalvprovet bevisar ingenting:")
        for f in _basfel:
            print("    * " + f[:140])
        return len(_basfel)

    def utan_ingar_rubrik(t):
        return t.replace('<h3 class="oa__ingar-rubrik" id="oaIngarRubrik"', '<h3 hidden="" x="', 1)

    def extra_div(t):
        return t.replace('<p class="oa__contact">', '<div class="oa__nytt"></div><p class="oa__contact">', 1)

    def fold_byter_niva(t):
        return t.replace('<details class="oa__fold" id="oaVillkor"',
                         '<section><details class="oa__fold" id="oaVillkor"', 1)

    def fack_forsvinner(t):
        return t.replace('<ul class="oa__rader" id="oaRader">', '<ul class="oa__rader">', 1)

    def ordningen_kastas_om(t):
        a = '<h3 class="oa__ingar-rubrik" id="oaIngarRubrik" hidden="">Allt som ingår</h3>'
        b = '<ul class="oa__ingar" id="oaIngar" hidden=""></ul>'
        if a in t and b in t:
            return t.replace(a + "\n      " + b, b + "\n      " + a, 1)
        return t

    PROV = [("en rubrik forsvinner pa EN mall", "service", utan_ingar_rubrik),
            ("en mall far ett element de andra inte har", "tillagg", extra_div),
            ("en fold hamnar en niva djupare", "batteri", fold_byter_niva),
            ("ett datafack tappar sitt id", "elcentral", fack_forsvinner),
            ("tva element byter ordning", "batteri", ordningen_kastas_om)]
    slapp = 0
    for namn, mall, f in PROV:
        muterad = dict(bas)
        muterad[mall] = f(bas[mall])
        if muterad[mall] == bas[mall]:
            print("  TRAFF0 %-44s mutationen andrade INGENTING (inget bevis)" % namn)
            slapp += 1
            continue
        _, fel = kor(tyst=True, sidor=muterad)
        # FELET MASTE NAMNA DEN MUTERADE MALLEN. Annars kan en rad bli ROD av
        # nagot annat - en baslinje som redan var trasig - och mutationen
        # bevisar ingenting. Uppmatt: tva av fem mutationer rapporterade en
        # baslinjebugg i ett annat mallpar och las som bevis.
        mitt = [f for f in fel if mall in f]
        if mitt:
            print("  ROTT  %-44s %s" % (namn, mitt[0][:100]))
        elif fel:
            print("  OKLAR %-44s rott, men om %s: %s" % (namn, "nagot annat", fel[0][:70]))
            slapp += 1
        else:
            print("  GRONT %-44s SLAPPTE FORBI" % namn)
            slapp += 1
    print()
    print("%d mutationer, %d slapp forbi" % (len(PROV), slapp))
    return slapp


if __name__ == "__main__":
    if "--sjalvprov" in sys.argv:
        raise SystemExit(1 if sjalvprov() else 0)
    n, fel = kor()
    if "--vagar" in sys.argv:
        for r in rader(skelett((HAR / "fall" / "laddbox.html").read_text(encoding="utf-8"))):
            print("  " + r)
        print()
    print("5 mallar, %d element i skelettet" % n)
    if fel:
        print("\n%d FEL:" % len(fel))
        for f in fel:
            print("  * " + f)
        raise SystemExit(1)
    print("ETT skelett for alla fem")
