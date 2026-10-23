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
    gt, rot = "gron-teknik" in potter, "rot" in potter
    if gt and rot: forsta, andra = "inkl. moms, efter grön teknik och ROT", "Avdragen dras direkt på fakturan."
    elif gt:       forsta, andra = "inkl. moms, efter grön teknik", "Avdraget dras direkt på fakturan."
    elif rot:      forsta, andra = "inkl. moms, efter ROT-avdrag", "Avdraget dras direkt på fakturan."
    else:          forsta, andra = "inkl. moms", ""
    delar = [forsta + ".", andra]
    if "inget" in potter and (gt or rot): delar.append("Rader utan avdrag är märkta.")
    if rot: delar.append("ROT förutsätter att du har avdragsutrymme kvar.")
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
    tot_str = "{:,}".format(tot).replace(",", " ") + " kr"
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

print("%d kontroller" % kontroller)
if fel:
    print("\n%d FEL:" % len(fel))
    for f in fel:
        print("  * " + f)
    sys.exit(1)
print("alla gröna")
