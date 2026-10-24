#!/usr/bin/env python3
"""Oraklet. Kör efter varje bygge:  python3 prov.py

Inget här är en bedömning. Varje kontroll är ett mått med ett svar, och en
felande kontroll säger VILKEN fil och VILKET värde som bröt den.
"""
import json
import pathlib
import re
import sys
import unicodedata

HAR = pathlib.Path(__file__).resolve().parent
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]
POTTER = {"gron-teknik", "rot", "inget"}

# Löften som redan står i den godkända copyn. ETT NYTT löfte om leverans får
# inte smyga in: prototypen har ingen transport, och en sida som lovar mer än
# den gör gör ett erkänt gap värre. Samma lista som offertrepots META.
KANDA_LOFTEN = ["registrerad", "registrerat", "tagit emot", "mottagen"]
NYA_LOFTEN = ["skickad", "skickat", "mejlad", "mejlat", "bekräftelse på mejl",
              "ett mejl är på väg", "du får ett mejl", "sparad", "sparat",
              "vidarebefordrad", "lagd i", "i vårt system"]

fel = []
kontroller = 0


def kolla(ok, text):
    global kontroller
    kontroller += 1
    if not ok:
        fel.append(text)


def synlig(html):
    """Texten en kund faktiskt ser. Kommentarer och svg räknas inte: den
    delade skärmen bär '<!-- 1 · confirmation -->' och den första versionen av
    det här oraklet stoppade på mittpunkten i en kommentar."""
    s = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    s = re.sub(r"<svg.*?</svg>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]*\shidden(=\"\")?[^>]*>.*?</[a-zA-Z0-9]+>", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return s.replace("&nbsp;", " ").replace("&amp;", "&")


def tal_i(s):
    """Varje belopp i en sträng, som heltal. '14 345 kr' -> 14345."""
    return {int(t.replace(" ", "").replace(" ", ""))
            for t in re.findall(r"(\d[\d  ]*)\s*kr", s)}


def pottrad(potter):
    """Ägarens lydelse D3, 24 oktober, ordagrant samma som offertrepots
    offerter/tillagg/offert.py:pottrad. Oraklet skriver den SJÄLVT i stället
    för att läsa sidans, annars provar det bara att sidan är lika med sig
    själv. Ändras lydelsen ändras två ställen, och det är meningen."""
    gt, rot = "gron-teknik" in potter, "rot" in potter
    namn = [n for n, med in (("Grön teknik", gt), ("ROT", rot)) if med]
    if namn:
        forsta = "inkl. moms, efter skattereduktion (%s)" % " och ".join(namn)
        andra = ("Avdragen" if len(namn) > 1 else "Avdraget") + " dras direkt på fakturan."
    else:
        forsta, andra = "inkl. moms", ""
    delar = [forsta + ".", andra]
    if "inget" in potter and namn: delar.append("Rader utan avdrag är märkta.")
    return forsta, " ".join(d for d in delar if d)


# ---------------------------------------------------------------- 1. källan
js = (HAR / "script.js").read_text(encoding="utf-8")
js_kod = re.sub(r"/\*.*?\*/", " ", js, flags=re.S)
js_kod = re.sub(r"(?m)^\s*//.*$", " ", js_kod)
for ord_ in ("fetch(", "XMLHttpRequest", "sendBeacon", "FormData",
             "localStorage", "sessionStorage", "URLSearchParams", "location.search"):
    kolla(ord_ not in js_kod, "script.js bär %s. Sidan är en läsare: ingen transport, "
                          "inga URL-parametrar, ingen lagring i webbläsaren." % ord_)

index = (HAR / "index.html").read_text(encoding="utf-8")
kolla(not tal_i(synlig(index)), "index.html bär ett belopp i markupen: %s. Utan kontrakt "
                                "ska sidan inte visa ett enda tal." % tal_i(synlig(index)))
kolla("[Bokare]" not in index, "index.html bär platshållaren [Bokare]. Hakparenteser får "
                               "aldrig nå en kund: saknas namnet skrivs meningen utan det.")
kolla("2026-0" not in index, "index.html bär ett offertnummer. Exempelvärden i produktionsmallen "
                             "läcker till en kund som får en sida utan kontrakt.")
kolla("<form" not in index and "<button" not in index,
      "index.html bär en kontroll. Sidan visar räknade tal och ska inte ha något att trycka på "
      "utöver telefonlänken.")

# ---------------------------------------------------------------- 2. kontrakten
for mall in MALLAR:
    f = HAR / "exempel" / (mall + ".json")
    d = json.loads(f.read_text(encoding="utf-8"))
    o, offert = d["order"], d["offert"]
    kolla(d.get("priser_ar") == "netto",
          "%s: priser_ar är %r. Alla belopp är netto, efter avdrag och inklusive moms "
          "(ägarbesked 2026-10-22). Fältet har ingen default." % (mall, d.get("priser_ar")))
    kolla(isinstance(d.get("kontrakt_version"), int), "%s: kontrakt_version saknas" % mall)
    kolla(isinstance(o.get("rader"), list),
          "%s: rader är inte en lista. Den får vara tom, aldrig null." % mall)

    summa = 0
    potter = set()
    if o.get("paket"):
        p = o["paket"]
        kolla(p.get("avdrag") in POTTER, "%s: paketets avdrag är %r, ska vara ett av %s"
                                         % (mall, p.get("avdrag"), sorted(POTTER)))
        if isinstance(p.get("belopp"), int):
            summa += p["belopp"]; potter.add(p["avdrag"])
    for r in o["rader"]:
        kolla(r.get("avdrag") in POTTER,
              "%s: raden %r har avdrag %r. Vokabulären är gron-teknik, rot, inget, och bara den: "
              "elcentralens 'gt' och laddboxens data-rot mappas HIT av den som fyller kontraktet."
              % (mall, r.get("namn"), r.get("avdrag")))
        if r.get("typ") == "intresseanmalan":
            kolla(r.get("belopp") is None,
                  "%s: intresseanmälan %r bär ett belopp. Den summeras aldrig." % (mall, r.get("namn")))
        if r.get("typ") == "mellanskillnad":
            kolla(bool(r.get("i_stallet_for")),
                  "%s: mellanskillnaden %r saknar i_stallet_for. Utan den läser kunden att en "
                  "laddkabel kostar %s kr." % (mall, r.get("namn"), r.get("belopp")))
        if isinstance(r.get("belopp"), int):
            summa += r["belopp"]; potter.add(r["avdrag"])
        if isinstance(r.get("antal"), int) and r["antal"] > 1 and isinstance(r.get("styckpris"), int):
            kolla(r["antal"] * r["styckpris"] == r.get("belopp"),
                  "%s: %r: %d gånger %d är inte %s" % (mall, r.get("namn"), r["antal"],
                                                       r["styckpris"], r.get("belopp")))
    kolla(o.get("total") == summa,
          "%s: totalen %s mot paket plus rader %s. Går det inte ihop renderar sidan inget "
          "totalbelopp alls." % (mall, o.get("total"), summa))
    if offert.get("ar_tillagg"):
        kolla(bool(offert.get("moderreferens")),
              "%s: ar_tillagg utan moderreferens. Kunden ser två orelaterade nummer." % mall)
    # Inget fält i kontraktet får bära ett avdragsBELOPP. Ägardirektiv 2026-10-23.
    platt = json.dumps(d, ensure_ascii=False)
    for forbjudet in ('"rot_belopp"', '"avdrag_belopp"', '"rotavdrag"', '"gron_teknik_belopp"',
                      '"fore_avdrag"', '"sats"', '"arbetsandel"'):
        kolla(forbjudet not in platt,
              "%s: kontraktet bär %s. ROT-avdragets belopp får aldrig stå på en sida, och "
              "ett fält som finns kommer att renderas." % (mall, forbjudet))

# ---------------------------------------------------------------- 3. de byggda sidorna
for mall in MALLAR:
    d = json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8"))
    h = (HAR / "fall" / (mall + ".html"))
    kolla(h.exists(), "%s: fall/%s.html saknas, kör python3 bygg.py" % (mall, mall))
    if not h.exists():
        continue
    html = h.read_text(encoding="utf-8")
    syn = synlig(html)

    kolla("<script" not in html,
          "%s: den byggda sidan bär JavaScript. Den ska fungera med JS avstängt." % mall)
    kolla("data-oa-fel" not in html,
          "%s: renderaren flaggade kontraktsfel: %s"
          % (mall, (re.search(r'data-oa-fel="([^"]*)"', html) or [None, "?"])[1]))
    kolla("[Bokare]" not in html and "[GAP]" not in syn,
          "%s: en platshållare står i den byggda sidan" % mall)
    for ord_ in ("hela Sverige", "rikstäckande", "hela landet"):
        kolla(ord_ not in syn, "%s: %r står på sidan. Storstockholm och Mälardalen, "
                               "aldrig nationellt." % (mall, ord_))
    t = re.search("[–—·]", syn)
    kolla(t is None, "%s: tankstreck eller mittpunkt i synlig text: %r"
                     % (mall, syn[max(0, (t.start() if t else 0) - 40):(t.start() if t else 0) + 40]))
    for lofte in NYA_LOFTEN:
        kolla(lofte not in syn.lower(),
              "%s: sidan lovar %r. Prototypen har ingen transport och får inte lova mer "
              "än den redan gör." % (mall, lofte))

    # ALLA TAL PÅ SIDAN KOMMER UR KONTRAKTET. Ingen rad på sidan får bära ett
    # belopp som inte står i kontraktet, och det är också skyddet mot att ett
    # ROT-belopp någonsin dyker upp: det finns inget fält att hämta det ur.
    tillatna = set()
    kontrakt_str = json.dumps(d, ensure_ascii=False)
    for m2 in re.finditer(r'"(?:belopp|total|styckpris)":\s*(\d+)', kontrakt_str):
        tillatna.add(int(m2.group(1)))
    tillatna |= tal_i(kontrakt_str.replace("\\u00a0", " "))
    pa_sidan = tal_i(syn)
    kolla(pa_sidan <= tillatna,
          "%s: sidan visar belopp som inte står i kontraktet: %s"
          % (mall, sorted(pa_sidan - tillatna)))

    # Totalen står EN gång. Två tal med samma namn på samma kort läser som
    # två olika sanningar.
    tot = d["order"]["total"]
    tot_str = "{:,}".format(tot).replace(",", " ") + " kr"
    kolla(syn.count(tot_str) == 1,
          "%s: totalen %r står %d gånger, väntade 1" % (mall, tot_str, syn.count(tot_str)))

    # Finstilten och kvittonoten säger samma sak om moms och avdrag, och den
    # säger det potterna faktiskt är.
    potter = set()
    if d["order"].get("paket") and isinstance(d["order"]["paket"].get("belopp"), int):
        potter.add(d["order"]["paket"]["avdrag"])
    for r in d["order"]["rader"]:
        if isinstance(r.get("belopp"), int):
            potter.add(r["avdrag"])
    kort, hel = pottrad(potter)
    kolla(html.count('<span class="oa__kvitto-not" id="oaKvittoNot">%s</span>' % kort) == 1,
          "%s: kvittonoten säger inte %r" % (mall, kort))
    kolla(hel in syn, "%s: finstilten säger inte %r" % (mall, hel))
    kolla("Läs våra köpvillkor" in syn,
          "%s: köpvillkorslänken saknas. Villkoren ska nå papperet." % mall)

    # ---- INVARIANT 1. ETT BELOPP BRYTS ALDRIG MITT ITU. -------------------
    # Ägarbeslut A8, 24 oktober: hårdspatie (U+00A0) BÅDE som
    # tusentalsavgränsare OCH före "kr". Ett vanligt mellanslag tillåter
    # radbrytning, och "14 345" på en rad med "kr" på nästa är två saker som
    # läser som en felskrivning på en sida kunden just har bundit sig vid.
    # UPPMÄTT FÖRE: 24 av 24 belopp på de fem sidorna bar vanligt mellanslag
    # före kr, och noten om grannrabatten bar det också i "1 500 kr".
    # MÄTS I DEN SYNLIGA TEXTEN, inte i källan: Chrome skriver U+00A0 som
    # &nbsp; i den dumpade DOM:en, så en regex mot rå markup svarar fel.
    belopp_i_syn = [m2.group(0).strip() for m2 in re.finditer(r"[\d\u00a0 ]*\d.kr\b", syn)]
    for b in belopp_i_syn:
        kolla(b.endswith("\u00a0kr"),
              "%s: beloppet %r har vanligt mellanslag före kr. Hårdspatie på båda "
              "ställena, ägarbeslut A8 24 okt." % (mall, b))
    for m2 in re.finditer(r"(?<!\d)(\d{1,3})( )(\d{3})(?!\d)", syn):
        kolla(False, "%s: tusentalsavgränsaren i %r är ett vanligt mellanslag."
                     % (mall, m2.group(0)))
    # EN SLINGA SOM INTE SNURRAR ÄR EN GRÖN RUTA UTAN MÄTNING. Slutar sidan
    # rendera belopp passerar kontrollerna ovan genom att aldrig köras.
    # Därför också ett POSITIVT påstående: varje tal kontraktet bär ska stå
    # på sidan i husets form, och antalet funna belopp ska nå dit.
    vantade = []
    if d["order"].get("paket") and isinstance(d["order"]["paket"].get("belopp"), int):
        vantade.append(d["order"]["paket"]["belopp"])
    vantade += [r["belopp"] for r in d["order"]["rader"] if isinstance(r.get("belopp"), int)]
    vantade.append(d["order"]["total"])
    for v in vantade:
        kolla(("{:,}".format(v).replace(",", "\u00a0") + "\u00a0kr") in syn,
              "%s: beloppet %d står inte på sidan i husets form" % (mall, v))
    kolla(len(belopp_i_syn) >= len(vantade),
          "%s: %d belopp hittades i texten men kontraktet bär %d. Mätningen letade "
          "efter fel sak." % (mall, len(belopp_i_syn), len(vantade)))

    # Blandade potter: VARJE rad med ett belopp är märkt. En pott: ingen rad.
    etiketter = html.count('<small class="oa__rad-pott">')
    med_belopp = sum(1 for r in d["order"]["rader"] if isinstance(r.get("belopp"), int))
    med_belopp += 1 if (d["order"].get("paket") and isinstance(d["order"]["paket"].get("belopp"), int)) else 0
    if len(potter) > 1:
        kolla(etiketter == med_belopp,
              "%s: %d potter men %d av %d prisrader är märkta"
              % (mall, len(potter), etiketter, med_belopp))
    else:
        kolla(etiketter == 0, "%s: en pott men %d rader bär en pottmärkning" % (mall, etiketter))


# ------------------------------------------------- 4. att felet faktiskt stänger
# De tre reglerna som ska stänga sidan i stället för att gissa, körda på
# riktigt i webbläsaren. En regel som bara står i en kommentar är ingen regel.
if "--snabb" not in sys.argv:
    import bygg
    bas = json.loads((HAR / "exempel" / "laddbox.json").read_text(encoding="utf-8"))

    def rendera_med(andra):
        d = json.loads(json.dumps(bas))
        andra(d)
        tmp = HAR / "exempel" / "_prov.json"
        tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        try:
            return bygg.rendera(tmp)
        finally:
            tmp.unlink(missing_ok=True)

    def nollar_totalen(namn, andra):
        html = rendera_med(andra)
        har_total = 'id="oaKvitto" hidden' not in html
        kolla(not har_total, "%s: sidan visade ändå ett totalbelopp. Fel i kontraktet ska "
                             "stänga talet, inte gissa det." % namn)
        kolla("data-oa-fel" in html, "%s: renderaren flaggade inget fel" % namn)

    def satt_total(d): d["order"]["total"] = d["order"]["total"] + 1
    nollar_totalen("totalen stämmer inte med raderna", satt_total)

    def satt_pott(d): d["order"]["rader"][0]["avdrag"] = "gt"
    nollar_totalen("en rad bär elcentralens 'gt' i stället för 'gron-teknik'", satt_pott)

    def satt_brutto(d): d["priser_ar"] = "brutto"
    nollar_totalen("priser_ar säger brutto", satt_brutto)

    # Och tvärtom: utan kontrakt står den godkända sidan kvar, utan ett enda tal.
    tom = rendera_med(lambda d: d.clear())
    kolla('id="oaOrder" hidden' in tom and 'id="oaKvitto" hidden' in tom,
          "ett tomt kontrakt ska lämna sidan som den var, utan ordersektion och utan kvitto")

# ------------------------------------------------- 5. husets skalor
# INVARIANT 2. SJU TYPSTORLEKAR, INTE FLER.
# MÄTT I WEBBLÄSAREN, inte läst ur CSS: en clamp, en ärvd procent eller ett
# !important i en mediafråga syns inte i källan men syns i renderingen. Och
# vid TVÅ bredder, för en fluid storlek är rätt på en bredd och fel på nästa:
# rubriken mätte 27 px vid 390 och 35,98 vid 1180, alltså fel på båda.
# UPPMÄTT FÖRE: elva storlekar vid 390 (27, 19, 17, 16, 15, 14.5, 14, 13,
# 12.5, 12, 11) där huset har sju.
if "--snabb" not in sys.argv:
    sys.path.insert(0, str(HAR / "verktyg"))
    import typ as _typ
    for mall in MALLAR:
        for bredd in (390, 1180):
            d = _typ.matt(HAR / "fall" / (mall + ".html"), bredd)
            ute = _typ.utanfor_skalan(d)
            kolla(not ute,
                  "%s @ %d: %s ligger utanför husets sju typstorlekar %s"
                  % (mall, bredd, ute, list(_typ.SKALA)))
            kolla(len(d["storlekar"]) > 0, "%s @ %d: sonden hittade inga textelement alls, "
                                           "alltså mätte den ingenting" % (mall, bredd))
            # Och vikterna. Typsnittsfilen klamrar tyst en vikt den inte har,
            # så en 900 som ingen skrivit syns bara om man frågar efter den.
            viktfel = _typ.utanfor_vikterna(d)
            kolla(not viktfel,
                  "%s @ %d: vikten %s renderas men huset har bara %s"
                  % (mall, bredd, viktfel, list(_typ.VIKTER)))

# INVARIANT 3. VARJE LÄNGD UR HUSETS SKALOR.
# Läses ur styles.css, för det är där ett tal utanför skalan skrivs. Undantagen
# står namngivna i verktyg/skala.py och är få: hårlinjer, skuggor, fokusringen,
# aurorans bredder, kortets max-width och bockens glyf.
# UPPMÄTT FÖRE: 51 deklarationer utanför skalan, 28 distinkta värden.
sys.path.insert(0, str(HAR / "verktyg"))
import skala as _skala
_ute = _skala.bryter((HAR / "styles.css").read_text(encoding="utf-8"))
kolla(not _ute, "styles.css: %d längder utanför husets skalor: %s"
                % (len(_ute), [(r, s2, e, px) for r, s2, e, px, _ in _ute][:8]))
# Och att mätaren faktiskt mäter: den ska hitta kortets 540 px, ett tal som
# står i filen och är ett namngivet undantag. En parser som slutar träffa
# något rapporterar noll fel, vilket är samma gröna ruta som "allt är rätt".
_langder = _skala.langder((HAR / "styles.css").read_text(encoding="utf-8"))
kolla(any(sel.endswith(".oa__card") and px == 540 for _, sel, _, px in _langder),
      "styles.css: mätaren hittade inte .oa__card max-width 540px, alltså läser den fel")
kolla(len(_langder) >= 20,
      "styles.css: mätaren hittade bara %d längder, väntade minst 20" % len(_langder))

# INVARIANT 4. VARJE STRÄNG KUNDEN SER ÄR OFFERTENS EGEN, ORDAGRANT.
# Det här provet läser OFFERTREPOT. Ett orakel som bara läser sitt eget repo
# kan inte upptäcka att sanningskällan rört sig, och det var precis så tre fel
# överlevde till 24 oktober. Hittas inte repot är provet INTE kört, och det
# sägs rakt ut i stället för att räknas som grönt.
NORDSTJARNA = pathlib.Path.home() / "Desktop" / "Claude Code" / "laddboxoffert"
_ordagrant_kord = False
if NORDSTJARNA.exists():
    import ordagrant as _ordagrant
    _antal, _fel = _ordagrant.kor(NORDSTJARNA, tyst=True)
    for f in _fel:
        kolla(False, "ordagrant: " + f)
    kolla(_antal >= 40, "ordagrant: bara %d strängar kontrollerade, väntade minst 40" % _antal)
    _ordagrant_kord = _antal

print("%d kontroller" % kontroller)
if _ordagrant_kord:
    print("ordagrant: %d kundsträngar kontrollerade mot offertrepot" % _ordagrant_kord)
else:
    print("EJ KÖRT: ordagrantprovet. Hittar inte offertrepot på %s.\n"
          "          Kör det för hand: python3 verktyg/ordagrant.py <sökväg>" % NORDSTJARNA)
if fel:
    print("\n%d FEL:" % len(fel))
    for f in fel:
        print("  * " + f)
    sys.exit(1)
print("alla gröna")
