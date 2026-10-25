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


def _strangar_i(o, vag=""):
    """Varje sträng i ett kontrakt som inte är en not. Nycklar med _ är
    källor och kommentarer och når aldrig kunden."""
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith("_"):
                continue
            yield from _strangar_i(v, vag + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from _strangar_i(v, vag + "[%d]" % i)
    elif isinstance(o, str) and o.strip():
        yield (vag, o)


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


# ÄGARSVAR 48, 25 OKTOBER, ORDAGRANT:
#   "Ta bort den raden från alla offerter samt orderbekräftelse. Detta står
#    redan i våra köpvillkor och är inte vårt ansvar utan kundens."
# Raden är "ROT förutsätter att du har avdragsutrymme kvar." Offertrepot tog
# bort den ur alla fem mallarna och satte ett generiskt orakel i
# gemensamt/orakel.py:inget_avdragsutrymme. Det här är samma orakel på den
# här sidan, och det är inte dekoration: meningen stod i KONTRAKT.md §4 som
# en ÄGARGRIND, alltså som något som kunde komma tillbaka. Nu kan den inte.
#
# TRE VÄGAR IN, ALLA TRE STÄNGDA. Meningen kan komma ur markupen, ur
# pottrad() i script.js, eller ur en sträng i ett kontrakt. Oraklet läser
# alla tre, för det är billigare än att gissa vilken väg nästa person tar.
def inget_avdragsutrymme(text, var):
    traff = re.findall(r"[^.]{0,70}avdragsutrymme[^.]{0,40}", text)
    kolla(not traff, "%s: meningen om avdragsutrymme står här: %r. ÄGARSVAR 48, 25 okt: "
                     "det är kundens ansvar, det står i köpvillkoren, och att nämna det "
                     "skapar en osäkerhet hos kunden."
                     % (var, " ".join(traff[0].split())[:120] if traff else ""))


# ÄGARSVAR 46, 25 OKTOBER: "Ja, lägg till datum."
# Samma tabell som script.js, SKRIVEN HÄR OCKSÅ och med flit. Läste oraklet
# sidans egen form provade det bara att sidan är lika med sig själv, precis
# som pottrad() ovan. Ändras formen ändras två ställen, och det är meningen.
MANADER = ["januari", "februari", "mars", "april", "maj", "juni",
           "juli", "augusti", "september", "oktober", "november", "december"]


def datum_lang(iso):
    """'2026-10-25' -> '25 oktober 2026'. None när datumet inte finns i
    kalendern: 2026-02-30 passerar varje regex men är inte en dag."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (iso or "").strip())
    if not m:
        return None
    ar, man, dag = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        import datetime
        datetime.date(ar, man, dag)
    except ValueError:
        return None
    return "%d %s %d" % (dag, MANADER[man - 1], ar)


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

# MARKUPEN, INTE DEN SYNLIGA TEXTEN. Första versionen läste synlig(index),
# och synlig() tar bort dolda element. I index.html är VARJE fyllbart element
# dolt tills ett kontrakt fyller det, så kontrollen mätte en nästan tom
# sträng och var grön av fel skäl. UPPMÄTT: meningen inskriven i
# <p class="oa__fin" ... hidden> gav exit 0 och noll fel.
_utan_kommentarer = re.sub(r"<!--.*?-->", " ", index, flags=re.S)
inget_avdragsutrymme(_utan_kommentarer, "index.html")
inget_avdragsutrymme(js, "script.js")

# ÄGARSVAR 46: INGET DATUM I MARKUPEN. Datumet är en parameter per fall och
# ska komma ur kontraktet. Det är exakt det här felet offertrepots
# elcentralmall bär i dag: "27 oktober 2026" står som bokstavlig sträng i
# markupen och byts med str.replace vid varje bygge. En sida som får ett
# kontrakt utan datum ska skriva ingen mening alls.
# Kommentarerna bort först: de FÖRKLARAR beslutet och daterar det ("ägarsvar
# 46, 25 oktober"). Det är inte ett datum i markupen, det är en källa.
_markup = _utan_kommentarer
for _m in MANADER:
    kolla(_m not in _markup,
          "index.html bär månaden %r. Acceptdatumet är en parameter per fall i kontraktet, "
          "aldrig en sträng i markupen." % _m)
kolla(not re.search(r"\d{4}-\d{2}-\d{2}", _markup),
      "index.html bär ett ISO-datum i markupen.")
kolla(not re.search(r"\d{4}-\d{2}-\d{2}", synlig(index)),
      "index.html bär ett datum i den synliga texten. Ingen platshållare, inget exempeldatum.")
# OCH ACCEPTDATUMET DRAR INTE MED SIG ETT GILTIG TILL. Ägardirektiv 23 okt:
# offerten har ingen giltighetstid. Fältet giltig_till_lang finns i kontraktet
# för avböjsskärmens tvilling och används inte här.
kolla("iltig" not in synlig(index),
      "index.html skriver något om giltighet. Offerten har ingen giltighetstid "
      "(ägardirektiv 23 okt), och ett acceptdatum är inte ett giltighetsdatum.")

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
    # ÄGARSVAR 46. Fältet finns i varje kontrakt, och är antingen null eller
    # ett datum som finns i kalendern. Ett fält som saknas är inte samma sak
    # som ett fält som är tomt: det första är en mall som inte vet om att
    # frågan finns, och då hårdkodar nästa person datumet i markupen.
    kolla("accepterad" in offert,
          "%s: offert.accepterad saknas helt. Fältet ska finnas även när det är null, "
          "annars vet nästa mall inte att datumet är en parameter (ägarsvar 46)." % mall)
    acc = offert.get("accepterad")
    kolla(acc is None or (isinstance(acc, str) and datum_lang(acc) is not None),
          "%s: offert.accepterad är %r. Antingen null eller ett datum i kalendern på "
          "formen 2026-10-25. Aldrig en färdigskriven mening, aldrig en platshållare."
          % (mall, acc))
    kolla(offert.get("giltig_till_lang") is None,
          "%s: giltig_till_lang är satt. Offerten har ingen giltighetstid (ägardirektiv "
          "23 okt), och acceptdatumet drar inte med sig ett giltig till." % mall)

    # ÄGARSVAR 48. Inte bara på sidan: en sträng i kontraktet renderas.
    for _vag, _s in ((v, s) for v, s in _strangar_i(d)):
        inget_avdragsutrymme(_s, "%s %s" % (mall, _vag))

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
    # Hela markupen utan kommentarer, av samma skäl som för index.html: ett
    # dolt element är fortfarande en mening som ett kontrakt kan tända.
    inget_avdragsutrymme(re.sub(r"<!--.*?-->", " ", html, flags=re.S), "%s (byggd sida)" % mall)

    # ---- ÄGARSVAR 46. ACCEPTDATUMET PÅ SIDAN -----------------------------
    # Mätningen är dubbelriktad med flit. Bär kontraktet ett datum SKA raden
    # stå där, i husets form, exakt en gång. Bär det inget datum får ordet
    # "Accepterad" inte stå på sidan alls: en rubrik utan sitt värde är en
    # platshållare med en annan frisyr.
    _acc = datum_lang(d["offert"].get("accepterad"))
    _rad = "Accepterad " + _acc if _acc else None
    _tatt = " ".join(syn.split())
    if _acc:
        kolla(_tatt.count(_rad) == 1, "%s: acceptdatumet %r står %d gånger på sidan, väntade 1"
                                      % (mall, _rad, _tatt.count(_rad)))
    else:
        kolla("Accepterad" not in syn,
              "%s: sidan säger 'Accepterad' men kontraktet har inget datum. Saknas datumet "
              "skrivs ingen mening alls." % mall)
        for _m in MANADER:
            kolla(_m not in syn, "%s: månaden %r står på sidan men kontraktet har inget "
                                 "acceptdatum. Varifrån kom den?" % (mall, _m))
    kolla("iltig" not in syn,
          "%s: sidan skriver något om giltighet. Offerten har ingen giltighetstid "
          "(ägardirektiv 23 okt) och ett acceptdatum är något annat." % mall)
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


# ------------------------------------- 3b. en accepterad offert, en bekräftelse
# ÄGARSVAR 56, 25 OKTOBER, ORDAGRANT:
#   "Vi måste se det som två olika offerter. Om en kund har accepterat en
#    laddboxoffert kommer de att få en orderbekräftelse för den. Har
#    elektrikern sedan varit där, gjort en offert för tillägg och skickat
#    den, får de en orderbekräftelse på tilläggen. Det blir inte en ny
#    orderbekräftelse på laddboxen. Alltså är det separat. För varje offert
#    som accepteras får man en unik orderbekräftelse."
#
# MÄTT, INTE ANTAGET. Offertnumren drog isär i offertrepot: fyra av fem
# mallar visade laddboxens 2026-0640 på acceptskärmen, och deras eget orakel
# läste re.search, alltså FÖRSTA träffen på sidan, som var just den delade
# skärmens 0640. Mallens eget nummer stod längre ner och sågs aldrig. Därför
# läses ALLA nummer på sidan här, och sidans eget nummer jämförs med det
# kontraktet säger att den ska visa.
_kontrakt = {m: json.loads((HAR / "exempel" / (m + ".json")).read_text(encoding="utf-8"))
             for m in MALLAR}
_nummer, _syn = {}, {}
for mall in MALLAR:
    h = HAR / "fall" / (mall + ".html")
    if not h.exists():
        continue
    _syn[mall] = synlig(h.read_text(encoding="utf-8"))
    o = _kontrakt[mall]["offert"]
    pa_sidan = sorted(set(re.findall(r"\d{4}-\d{4}", _syn[mall])))
    vantat = o.get("moderreferens") if o.get("ar_tillagg") else o.get("referens")
    kolla(len(pa_sidan) == 1,
          "%s: sidan visar %d olika offertnummer (%s). En sida som visar två nummer har "
          "inget offertnummer, och det var precis så servicemallen bar laddboxens 0640 "
          "i ett dygn." % (mall, len(pa_sidan), ", ".join(pa_sidan) or "inget"))
    kolla(pa_sidan == [vantat],
          "%s: sidan visar %s men kontraktet säger %s. Bekräftelsen ska bära sin EGEN "
          "offerts nummer." % (mall, pa_sidan, vantat))
    _nummer[mall] = pa_sidan[0] if len(pa_sidan) == 1 else None
    kolla(("Tillägg till offert" in _syn[mall]) == bool(o.get("ar_tillagg")),
          "%s: brickans etikett och ar_tillagg säger olika. Ett nummer som tillhör någon "
          "annan måste säga att det gör det." % mall)

# Två egna offerter får ALDRIG dela nummer.
_egna = [(m, _nummer.get(m)) for m in MALLAR
         if not _kontrakt[m]["offert"].get("ar_tillagg")]
for _i, (_a, _na) in enumerate(_egna):
    for _b, _nb in _egna[_i + 1:]:
        kolla(_na != _nb or _na is None,
              "%s och %s visar båda %s. För varje offert som accepteras får man en unik "
              "orderbekräftelse (ägarsvar 56)." % (_a, _b, _na))
kolla(len({_kontrakt[m]["offert"].get("mall") for m in MALLAR}) == len(MALLAR),
      "två kontrakt säger sig vara samma mall")

# TILLÄGGET DELAR MODERNS NUMMER MED FLIT, OCH DET PROVAS I STÄLLET FÖR ATT
# ANTAS. Det är en offert TILL en offert, och kunden ska se vilken. Men den
# får inte ärva vilket nummer som helst: numret ska vara exakt den mall
# modertyp pekar ut, och den mallens egen bekräftelse ska bära samma nummer.
for mall in MALLAR:
    o = _kontrakt[mall]["offert"]
    if not o.get("ar_tillagg") or mall not in _syn:
        continue
    mt = o.get("modertyp")
    kolla(mt in MALLAR, "%s: modertyp är %r, inte en av de fem mallarna. Då går det inte "
                        "att pröva vilken offert tillägget hör till." % (mall, mt))
    if mt in MALLAR:
        kolla(_nummer.get(mall) == _kontrakt[mt]["offert"].get("referens"),
              "%s: brickan visar %s men %s-offerten har %s. Tillägget hör till EN offert."
              % (mall, _nummer.get(mall), mt, _kontrakt[mt]["offert"].get("referens")))
        # OCH DEN UPPREPAR INTE MODERNS ORDER. "Det blir inte en ny
        # orderbekräftelse på laddboxen." Tre saker ur moderoffertens order
        # som aldrig får stå på tilläggets kvittens.
        mo = _kontrakt[mt]["order"]
        mt_total = "{:,}".format(mo["total"]).replace(",", " ") + " kr"
        kolla(mt_total not in _syn[mall],
              "%s: moderoffertens total %s står på tilläggets bekräftelse. Kunden har "
              "redan fått en bekräftelse på den." % (mall, mt_total))
        for _f, _v in (("order.rubrik", mo.get("rubrik")),
                       ("order.paket.namn", (mo.get("paket") or {}).get("namn"))):
            kolla(not _v or _v not in _syn[mall],
                  "%s: moderoffertens %s (%r) står på tilläggets bekräftelse. Tillägget "
                  "är en egen offert med egna rader." % (mall, _f, _v))
# VÄND PROV. Den första versionen av kontrollen ovan letade efter tilläggets
# RADNAMN på moderns sida och blev röd på "RFID-taggar", som står i båda
# kontrakten helt riktigt: det är samma katalogpost, vald två gånger, och
# bägge raderna är hämtade ur offertrepots egna urval. Provet hade alltså
# tvingat fram en ändring i DATAT för att bli grönt, vilket är felvänt
# (FALLOR.md: "ett prov som bevakar en gammal sanning stoppar rättningen,
# inte felet"). Det svar 56 faktiskt kräver är att EN bekräftelse bär EN
# offerts rader, varken fler eller färre. Det mäts här, åt båda hållen och
# för alla fem mallarna, och en rad som läcker mellan två bekräftelser syns
# då oavsett vad den heter.
def rader_pa(html):
    """Radernas namn i den ordning sidan skriver dem."""
    ut = []
    for li in re.findall(r'<li class="oa__rad[^"]*">(.*?)</li>', html, re.S):
        # Namnet ar texten i .oa__rad-text FORE forsta <small>. Priset bor i
        # en egen span efter, och underraderna i <small> inuti. Forsta
        # versionen klippte bara vid <small> och tog darfor med priset pa de
        # rader som inte har nagon underrad: "Liten5 990 kr".
        m = re.search(r'<span class="oa__rad-text">(.*?)(?:<small|</span>)', li, re.S)
        namn = re.sub(r"<[^>]+>", "", m.group(1) if m else "")
        ut.append(namn.replace("&amp;", "&").replace("&quot;", '"')
                      .replace("&nbsp;", "\u00a0").strip())
    return ut


def rader_i(d):
    """Radernas namn som kontraktet säger att de ska bli. Samma ordning som
    script.js bygger dem: paketet, raderna, de utestående löftena."""
    o, ut = d["order"], []
    if o.get("paket"):
        ut.append((o["paket"].get("namn") or o.get("rubrik") or "").strip())
    for r in o["rader"]:
        n = (r.get("namn") or "").strip()
        if r.get("variant"):
            n += ", " + r["variant"].strip()
        ut.append(n)
    for u in o.get("utestaende") or []:
        if u.get("text"):
            ut.append(u["text"].strip())
    return ut


for mall in MALLAR:
    h = HAR / "fall" / (mall + ".html")
    if not h.exists():
        continue
    _pa, _i = rader_pa(h.read_text(encoding="utf-8")), rader_i(_kontrakt[mall])
    kolla(_pa == _i,
          "%s: sidan visar raderna %s men kontraktet har %s. En accepterad offert ger EN "
          "bekräftelse med sina EGNA rader (ägarsvar 56): en rad för lite är en order kunden "
          "inte ser, en för mycket är en annan offerts rad." % (mall, _pa, _i))


# GRANSKNINGSSIDAN ÄR OCKSÅ EN KOPIA. fall/index.html är skriven för hand och
# bär de fem totalerna som text. Den är ingen kundyta, men den är en andra
# plats där samma tal står, och en andra plats är en plats som kan drifta.
# Samma skäl som hela talprovet finns av, en våning ner.
_oversikt = HAR / "fall" / "index.html"
if _oversikt.exists():
    _o = _oversikt.read_text(encoding="utf-8")
    for mall in MALLAR:
        _t = _kontrakt[mall]["order"]["total"]
        _vantad = "{:,}".format(_t).replace(",", " ")
        kolla('href="%s.html"' % mall in _o,
              "fall/index.html länkar inte till %s.html" % mall)
        kolla(_vantad + " kr" in _o or (_vantad.replace(" ", " ") + " kr") in _o,
              "fall/index.html säger inte %s kr för %s. Översikten är en andra kopia av "
              "samma tal och har driftat." % (_vantad, mall))


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

    # ---- ÄGARSVAR 46, KÖRT PÅ RIKTIGT I WEBBLÄSAREN --------------------
    # De fem kontrakten bär null, för ingen av de fem offerterna är
    # accepterad av någon: acceptdatumet uppstår när kunden trycker, och det
    # finns inte i något repo. En rendering som aldrig får ett datum bevisar
    # bara att sidan kan tiga. Därför provas mekanismen här med ett
    # PROVVÄRDE som aldrig lämnar den här funktionen: ingen fil i fall/ och
    # ingen kund ser det, och det är inte ett påstående om någon order.
    def satt_datum(v):
        return lambda d: d["offert"].update(accepterad=v)

    def ren(html):
        """Den synliga texten i en RÅ rendering. bygg.rendera lämnar kvar
        kontraktet i en script-tagg (stada() tar bort den först när filen
        sparas), så utan den här raden läser provet kontraktets JSON som om
        kunden såg den, och hittar ISO-datumet den just förbjöd.
        Mellanrummen slås ihop: markupen är `Accepterad <span>25 oktober
        2026</span>`, alltså en mening för kunden och två tecken mellanrum
        för en regex."""
        return " ".join(synlig(re.sub(r"<script.*?</script>", " ", html, flags=re.S)).split())

    _h = rendera_med(satt_datum("2026-10-25"))
    _vantad = "Accepterad " + datum_lang("2026-10-25")
    kolla(_vantad in ren(_h),
          "acceptdatum: kontraktet sa 2026-10-25 men sidan skrev inte %r" % _vantad)
    kolla('id="oaAccept" hidden' not in _h,
          "acceptdatum: raden stod kvar dold fastän kontraktet bar ett datum")
    kolla('id="oaKvitto" hidden' not in _h,
          "acceptdatum: ett giltigt datum stängde totalen")
    kolla("2026-10-25" not in ren(_h),
          "acceptdatum: sidan skrev ISO-datumet rakt av. Kunden läser svenska.")

    # ETT DATUM SOM INTE FINNS I KALENDERN STÄNGER. 2026-02-30 passerar varje
    # regex och är ingen dag. Sidan väljer inte vilka fel den bryr sig om:
    # ett kontrakt som har fel om datumet är ett kontrakt som har fel.
    nollar_totalen("accepterad 2026-02-30, en dag som inte finns", satt_datum("2026-02-30"))
    _h = rendera_med(satt_datum("2026-02-30"))
    kolla("februari" not in ren(_h) and "Accepterad" not in ren(_h),
          "acceptdatum: 2026-02-30 renderades ändå. Ett gissat datum på en bindande "
          "handling är värre än inget datum.")

    # Och utan datum skrivs ingen mening alls, aldrig en tom rubrik.
    _h = rendera_med(satt_datum(None))
    kolla("Accepterad" not in ren(_h),
          "acceptdatum: ordet 'Accepterad' stod på sidan utan ett datum efter sig")

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
_talen_kord = None
if NORDSTJARNA.exists():
    import ordagrant as _ordagrant
    _antal, _fel = _ordagrant.kor(NORDSTJARNA, tyst=True)
    for f in _fel:
        kolla(False, "ordagrant: " + f)
    kolla(_antal >= 40, "ordagrant: bara %d strängar kontrollerade, väntade minst 40" % _antal)
    _ordagrant_kord = _antal

    # INVARIANT 5. VARJE TAL KUNDEN SER ÄR HÄRLETT UR OFFERTREPOTS EGNA
    # KÄLLFILER. Ägarsvar 60, 25 okt: "Bygg det nu."
    # Kontrollerna ovan provar att sidans belopp står i KONTRAKTET och att
    # kontraktets belopp står på SIDAN. Kontraktet är en kopia av offertens
    # sanning, så den kedjan kan vara hel medan kopian har driftat. Det här
    # provet går till källfilen, räknar om varje härledning och slår upp
    # varje operand på plats.
    import talen as _talen
    _n, _felt, _rakn = _talen.kor(NORDSTJARNA, tyst=True)
    for f in _felt:
        kolla(False, "talen: " + f)
    kolla(_n >= 30, "talen: bara %d tal kontrollerade, väntade minst 30" % _n)
    kolla(_rakn["fil"] >= 20,
          "talen: bara %d operander slogs upp i offertrepots filer. Ett prov som bara "
          "jämför kontraktet mot sig självt är värdelöst." % _rakn["fil"])
    _talen_kord = (_n, _rakn)

print("%d kontroller" % kontroller)
if _ordagrant_kord:
    print("ordagrant: %d kundsträngar kontrollerade mot offertrepot" % _ordagrant_kord)
else:
    print("EJ KÖRT: ordagrantprovet. Hittar inte offertrepot på %s.\n"
          "          Kör det för hand: python3 verktyg/ordagrant.py <sökväg>" % NORDSTJARNA)
if _talen_kord:
    print("talen:     %d tal kontrollerade, %d operander slagna i offertrepots filer, "
          "%d mot kontraktets egna tal, %d kundval"
          % (_talen_kord[0], _talen_kord[1]["fil"], _talen_kord[1]["kontrakt"],
             _talen_kord[1]["val"]))
else:
    print("EJ KÖRT: talprovet. Hittar inte offertrepot på %s.\n"
          "          Kör det för hand: python3 verktyg/talen.py <sökväg>" % NORDSTJARNA)
if fel:
    print("\n%d FEL:" % len(fel))
    for f in fel:
        print("  * " + f)
    sys.exit(1)
print("alla gröna")
