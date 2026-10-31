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
    """ÄGARENS LYDELSE 25 OKTOBER, ORDAGRANT, i två meningar:

        kvittonoten  "inkl. moms, efter skattereduktion"
        finstilten   "inkl. moms, efter skattereduktion. Avdragen dras
                      direkt på fakturan."

    Hans egna ord om den förra lydelsen: om noten i kvittot, "Här vill jag
    att vi har: 'inkl. moms, efter skattereduktion'", och om texten under
    raderna, "Här vill jag att vi använder följande ENBART: 'inkl. moms,
    efter skattereduktion. Avdragen dras direkt på fakturan.'"

    PARENTESEN ÄR BORTA, OCH MED DEN BÖJNINGEN. Till 25 oktober skrev den
    här funktionen "(ROT)" på elcentralen, "(Grön teknik)" på batteriet och
    "(Grön teknik och ROT)" på laddboxen, och böjde "Avdraget"/"Avdragen"
    efter hur många potter som räknades upp. Utan uppräkning finns inget att
    kongruera med, och ägaren skrev plural.

    UTAN AVDRAG STÅR BARA "inkl. moms". Den grenen är sanningen, inte en
    finess: har ingen rad en pott finns ingen skattereduktion att nämna.

    ORAKLET SKRIVER LYDELSEN SJÄLVT i stället för att läsa sidans, annars
    provar det bara att sidan är lika med sig själv. Ändras lydelsen ändras
    två ställen, och det är meningen."""
    if "gron-teknik" not in potter and "rot" not in potter:
        return "inkl. moms", "inkl. moms."
    forsta = "inkl. moms, efter skattereduktion"
    return forsta, forsta + ". Avdragen dras direkt på fakturan."


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
      "utöver telefonlänken och villkorsfolden.")
# EXAKT EN FOLD. Ägarens GLOBAL NOTERING 25 oktober gav sidan sin första
# riktiga kontroll, och den är avsiktlig: "denna länk och 'Läs våra
# köpvillkor' ligger under en dropdown som heter villkor som ligger längst
# ner på orderbekräftelsen". En andra <details> är däremot ingen beställning.
# RAKNAT UTAN KOMMENTARER. Kommentaren ovanfor folden citerar bade taggen och
# ett utdrag ur utskriftsregeln, och forsta versionen av den har kontrollen
# raknade dem: tre <details> i en fil som har en. Samma mathal som sveptes
# 24 oktober, dar en kontroll last den rATa markupen i stallet for sidan.
# TRE FOLDAR SEDAN 29 OKTOBER, OCH DET AR EN BESTALLNING.
# Agardokumentet samma dag: "Det vi behover lagga till ar ovanfor villkor.
# 1: Kostnader som kan tillkomma (som en dropdown). 2: Vad behover du gora
# innan installationen?" Kravet ar inte sankt utan preciserat: EXAKT tre
# foldar, med EXAKT de har tre rubrikerna, i EXAKT den har ordningen. En
# fjarde ar fortfarande ingen bestallning, och villkoren ska fortfarande
# sta sist.
_index_ren = re.sub(r"<!--.*?-->", " ", index, flags=re.S)
_FOLDAR = ["Kostnader som kan tillkomma", "Vad behöver du göra före installationen?", "Villkor"]
_index_rub = [re.sub(r"<svg.*", "", s, flags=re.S).strip()
              for s in re.findall(r"<summary>(.*?)</summary>", _index_ren, re.S)]
kolla(_index_rub == _FOLDAR,
      "index.html har foldarna %s, väntade %s i den ordningen." % (_index_rub, _FOLDAR))
kolla(_index_ren.count("<details") == 3 and _index_ren.count("<summary>Villkor") == 1,
      "index.html har %d <details> och %d summary som heter Villkor, väntade 3 och 1."
      % (_index_ren.count("<details"), _index_ren.count("<summary>Villkor")))
# OCH INGEN LÄNKADRESS I MARKUPEN. href sätts av renderaren ur kontraktet:
# ett tomt href i mallen är en trasig länk på varje sida som inte fylls.
kolla("ampy.se/kopvillkor" not in index,
      "index.html bär köpvillkorsadressen som fast text. Den kommer ur kontraktets "
      "villkor_url, annars kan de fem mallarna peka olika utan att någon ser det.")

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

    # ---- ÄGARENS 25 OKTOBER, I DATAT OCH INTE BARA I RENDERINGEN --------
    # Skyddet mot att en text kommer tillbaka ligger i att det inte finns
    # något fält att hämta den ur. Samma princip som ROT-beloppet.
    for _i, _u in enumerate(o.get("utestaende") or []):
        kolla("not" not in _u,
              "%s: utestaende[%d] bär fältet `not`. Noten under raderna utgick 25 oktober "
              "(\"Här vill jag att vi använder följande enbart\"), och ett fält som finns "
              "kommer någon att rendera." % (mall, _i))
    for _i, _p in enumerate(o.get("ingar") or []):
        kolla(isinstance(_p, str) and _p.strip(),
              "%s: ingar[%d] är %r, inte en sträng. Allt som ingår är en REN punktlista: "
              "ett objekt med ett spec-fält är brödtexten under punkten, och den utgick "
              "25 oktober." % (mall, _i, _p))

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
    # EN MENING OCH INGENTING MER UNDER RADERNA. Ägarens "enbart" 25 okt.
    # Mätt mot elementets hela innehåll, inte med ett "finns i": en andra
    # mening inskriven efter den rätta hade annars passerat.
    _fin = re.search(r'<p class="oa__fin" id="oaFin"[^>]*>(.*?)</p>', html, re.S)
    kolla(bool(_fin) and " ".join(_fin.group(1).split()) == hel,
          "%s: finstilten står som %r, väntade exakt %r"
          % (mall, " ".join(_fin.group(1).split()) if _fin else None, hel))

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

    # ---- BARA RUBRIKERNA OCH PRISET. ÄGARENS ORD 25 OKTOBER. -------------
    # VÄNT ORAKEL. Här stod till 25 oktober motsatsen: "blandade potter:
    # VARJE rad med ett belopp är märkt. En pott: ingen rad." Den kontrollen
    # bevakade en sanning ägaren just ersatt, och hade stoppat rättningen i
    # stället för felet (FALLOR.md). Den är vänd, inte raderad: samma rad
    # mäter nu att ingen rad är märkt, oavsett hur många potter ordern har.
    # Hans ord, ordagrant: "Jag vill bara att du ska ha själva rubrikerna,
    # 'i stället för 5 meter' och inte 'grön teknikavdrag', utan det gör
    # bara så att det här blir ännu mer klotterigt. Bara rubrikerna och
    # priset."
    kolla('oa__rad-pott' not in html,
          "%s: en rad bär en pottmärkning. Ägaren 25 okt: bara rubrikerna och priset."
          % mall)
    for _etikett in ("Grön teknik-avdrag", "ROT-avdrag", "Utan avdrag"):
        kolla(_etikett not in syn,
              "%s: %r står på sidan. Pottmärkningen vid raden utgick 25 oktober; "
              "vilken pott ordern har säger finstilten en gång." % (mall, _etikett))
    # OCH SPECEN STÅR KVAR. Samma mening tar bort märkningen och behåller
    # det som säger vad kunden får. Utan en positiv mätning kunde nästa
    # person ta bort <small> helt och få grönt: "Laddkabel 22 kW, 10 meter"
    # utan "i stället för 5 meter" säger att en laddkabel kostar 200 kr.
    for r in d["order"]["rader"]:
        if r.get("typ") == "mellanskillnad" and r.get("i_stallet_for"):
            kolla(("i stället för " + r["i_stallet_for"]) in syn,
                  "%s: raden %r har tappat 'i stället för %s'. Specen säger vad kunden "
                  "får och står kvar; det var pottmärkningen som gick bort."
                  % (mall, r.get("namn"), r["i_stallet_for"]))

    # ---- FINSTILTEN SÄGER INGET OM VILKA POTTER DET ÄR -------------------
    # Ägarens ord om kvittonoten: "Under att betala längst upp står även:
    # 'inkl. moms, efter skattereduktion (Grön teknik och ROT)'. Här vill
    # jag att vi har: 'inkl. moms, efter skattereduktion'." Parentesen är
    # ett eget mått: pottrad() ovan kan skrivas om utan att någon märker
    # att den gamla formen kommit tillbaka på en av fem sidor.
    for _form in ("(Grön teknik och ROT)", "(Grön teknik)", "(ROT)",
                  "Rader utan avdrag är märkta"):
        kolla(_form not in syn,
              "%s: %r står på sidan. Den lydelsen utgick 25 oktober." % (mall, _form))

    # ---- INGEN NOT UNDER RADERNA -----------------------------------------
    # "Här vill jag att vi använder följande ENBART." Blocket under raderna
    # är en mening och ingenting mer.
    kolla('oa__not' not in html,
          "%s: noten under raderna är tillbaka. Ägaren 25 okt: enbart finstiltsmeningen."
          % mall)
    kolla("Upp till" not in syn and "ändras inte förrän" not in syn,
          "%s: grannrabattnoten står på sidan." % mall)

    # ---- ALLT SOM INGÅR ÄR EN REN PUNKTLISTA -----------------------------
    # "Här ska det, och jag vet att det här var feedback tidigare, bara vara
    # en punktlista." Mätt i markupen: en punkt är <li><bock><span>text</span>,
    # och ett andra <span> INNE i det spannet är brödtexten som gick bort.
    for _lista in re.findall(r'<ul class="oa__ingar"[^>]*>(.*?)</ul>', html, re.S):
        for _punkt in re.findall(r"<li>(.*?)</li>", _lista, re.S):
            # Bocken ar ett <span class="oa__bock">, texten ett <span>. Ett
            # ANDRA textspann inne i textspannet var specens egen rad.
            _efter_bock = re.sub(r'<span class="oa__bock".*?</span>', "", _punkt, flags=re.S)
            kolla(_efter_bock.count("<span>") == 1,
                  "%s: en punkt i Allt som ingår bär brödtext under sig: %r. Ägaren 25 okt: "
                  "bara en punktlista." % (mall, re.sub(r"<[^>]+>", " ", _punkt).strip()[:70]))

    # ---- VILLKOREN LIGGER I EN FOLD LÄNGST NER ---------------------------
    # Ägarens GLOBAL NOTERING 25 oktober. Fyra mått, för "det finns en
    # dropdown" är inte samma sak som "länken ligger i den".
    # TRE FOLDAR, OCH VILLKOREN SIST. Kontrollen tog fram forsta <details>
    # och provade den; sedan 29 oktober ar den forsta "Kostnader som kan
    # tillkomma", sa den hade provat fel fold och sagt att folden heter fel.
    # Den letar nu upp villkorsfolden PA SIN RUBRIK och kraver att den star
    # sist, vilket ar det agaren faktiskt bad om ("langst ner").
    _ren = re.sub(r"<!--.*?-->", " ", html, flags=re.S)
    _rub = [re.sub(r"<svg.*", "", s, flags=re.S).strip()
            for s in re.findall(r"<summary>(.*?)</summary>", _ren, re.S)]
    kolla(_rub == _FOLDAR,
          "%s: sidan har foldarna %s, väntade %s i den ordningen." % (mall, _rub, _FOLDAR))
    _foldar = re.findall(r"<details[^>]*>(.*?)</details>", _ren, re.S)
    _fold = _foldar[-1] if _foldar else None
    kolla(_fold is not None and _fold.lstrip().startswith("<summary>Villkor"),
          "%s: sista folden heter inte Villkor." % mall)
    kolla(_fold is not None and "Läs våra köpvillkor" in _fold,
          "%s: köpvillkorslänken ligger inte i villkorsfolden." % mall)
    # OCH DE TVA NYA FOLDARNA SYNS BARA NAR KONTRAKTET FYLLER DEM.
    # Service och tillagg har ingen av dem (agardokumentet ger dem till
    # laddbox, elcentral och batteri), och en rubrik som lovar innehall som
    # inte finns ar varre an ingen rubrik.
    for _id, _falt in (("oaKostnader", "kostnader"), ("oaForbered", "forberedelser")):
        _sek = re.search(r'<section[^>]*id="%s"([^>]*)>' % _id, _ren)
        _dold = bool(_sek) and "hidden" in _sek.group(1)
        _har = bool(d.get(_falt))
        kolla(bool(_sek) and _dold != _har,
              "%s: sektionen %s är %s men kontraktet %s %s."
              % (mall, _id, "dold" if _dold else "synlig",
                 "har" if _har else "saknar", _falt))
    kolla(syn.count("Läs våra köpvillkor") == 1,
          "%s: 'Läs våra köpvillkor' står %d gånger, väntade 1. Länken flyttade till "
          "folden och ska inte stå kvar i finstilten också."
          % (mall, syn.count("Läs våra köpvillkor")))
    _url = d["offert"].get("villkor_url")
    kolla(_fold is not None and ('href="%s"' % _url) in _fold,
          "%s: folden länkar inte till kontraktets villkor_url %r. Aldrig ett tomt href."
          % (mall, _url))
    # Och den ligger SIST bland kortets innehållsblock: under den står bara
    # avslutningen med telefonnumret, precis som offertens <footer class=
    # "o-fot"> står under villkorsfolden där.
    # TRE SEKTIONER BAR NU .oa__villkor, sedan 29 oktober: kostnaderna,
    # forberedelserna och villkoren delar form. Kontrollen tog [-2] och
    # traffade da forberedelserna. Den ankrar nu pa SEKTIONENS ID, som sager
    # vilken fold det ar, och kraver bade att villkoren ar nast sist och att
    # de tre star i agardokumentets ordning.
    _ids = re.findall(r'<section class="oa__section[^"]*" id="(oa\w+)"', _ren)
    _foldids = [i for i in _ids if i in ("oaKostnader", "oaForbered", "oaVillkor")]
    kolla(_foldids == ["oaKostnader", "oaForbered", "oaVillkor"],
          "%s: foldsektionerna star som %s, väntade kostnader, förberedelser, villkor."
          % (mall, _foldids))
    _sektioner = re.findall(r'<section class="oa__section([^"]*)"', _ren)
    kolla(len(_sektioner) >= 2 and " oa__villkor" in _sektioner[-2],
          "%s: villkorsfolden är inte näst sist bland sektionerna (%s). Den ska ligga "
          "längst ner, med bara avslutningen under sig." % (mall, _sektioner))


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


# ------------------------------------------------- 3c. EN MALL, EN SKILLNAD
# ÄGARENS ORD 25 OKTOBER, ORDAGRANT:
#   "När jag har gått igenom mallarna ser jag att varenda mall är lite
#    annorlunda. (...) Orderbekräftelsen kommer inte att ha olika mallar.
#    Det enda är ju tilläggsarbetet, eftersom 'Så här går vi vidare' är
#    annorlunda. Det är egentligen den enda skillnaden."
# Mätt i markupen, inte lovat i en kommentar: verktyg/samma-mall.py blankar
# det som är DATA och jämför resten tecken för tecken. Måttet är tvåsidigt:
# allt utanför steglistan ska vara samma tecken på alla fem, och exakt
# tilläggsmallens steglista ska skilja sig.
sys.path.insert(0, str(HAR / "verktyg"))
import importlib
_samma = importlib.import_module("samma-mall")
_n_mall, _fel_mall, _skiljer = _samma.kor(tyst=True)
for f in _fel_mall:
    kolla(False, f)
kolla(_n_mall >= 6, "samma-mall: bara %d kontroller kördes" % _n_mall)


# ------------------------------------------------- 3d. PROVFALLET, ÄGARSVAR 46
# "Ja, lägg till datum." Mekanismen är byggd, men de fem fallen bär null:
# ett acceptdatum uppstår när kunden trycker acceptera och finns inte i
# offertrepot. En sida som aldrig får ett datum bevisar bara att sidan kan
# tiga, så raden syns i ETT provfall, och provfallet mäts hårdare än de fem:
# det får inte vara en bakväg in för hittepå.
PROVFALL = "prov-acceptdatum"
_pf_k = HAR / "exempel" / (PROVFALL + ".json")
_pf_h = HAR / "fall" / (PROVFALL + ".html")
kolla(_pf_k.exists() and _pf_h.exists(),
      "provfallet saknas: %s och %s ska finnas (ägarsvar 46)" % (_pf_k.name, _pf_h.name))
if _pf_k.exists() and _pf_h.exists():
    _pf = json.loads(_pf_k.read_text(encoding="utf-8"))
    _lb = json.loads((HAR / "exempel" / "laddbox.json").read_text(encoding="utf-8"))
    # 1. KONTRAKTET ÄR LADDBOXENS, MED EXAKT ETT FÄLT ÄNDRAT. Allt annat på
    #    sidan är alltså laddboxfallets egna tal och strängar, redan
    #    kontrollerade mot offertrepot av ordagrant.py och talen.py.
    _utan = {k: v for k, v in _pf.items() if k != "_prov"}
    _utan["offert"] = {k: v for k, v in _utan["offert"].items() if k != "accepterad"}
    _lb_utan = dict(_lb); _lb_utan["offert"] = {k: v for k, v in _lb["offert"].items()
                                                if k != "accepterad"}
    kolla(json.dumps(_utan, sort_keys=True, ensure_ascii=False)
          == json.dumps(_lb_utan, sort_keys=True, ensure_ascii=False),
          "provfallet skiljer sig från laddbox.json i mer än offert.accepterad. Provet ska "
          "visa EN mekanism, inte bära ett eget påhittat fall.")
    kolla(_lb["offert"]["accepterad"] is None,
          "laddbox.json har fått ett acceptdatum. Ingen av de fem offerterna är accepterad "
          "av någon, och ett provvärde får inte förorena ett riktigt fall.")
    _pf_datum = _pf["offert"].get("accepterad")
    kolla(datum_lang(_pf_datum) is not None,
          "provfallets accepterad är %r, inget datum i kalendern" % _pf_datum)
    # 2. RADEN RENDERAS, I HUSETS SVENSKA FORM, EXAKT EN GÅNG.
    _pf_syn = " ".join(synlig(_pf_h.read_text(encoding="utf-8")).split())
    _vantad_rad = "Accepterad " + (datum_lang(_pf_datum) or "?")
    kolla(_pf_syn.count(_vantad_rad) == 1,
          "provfallet: %r står %d gånger på sidan, väntade 1"
          % (_vantad_rad, _pf_syn.count(_vantad_rad)))
    kolla(_pf_datum not in _pf_syn,
          "provfallet skriver ISO-datumet %r rakt av. Kunden läser svenska." % _pf_datum)
    kolla("iltig" not in _pf_syn,
          "provfallet skriver något om giltighet. Ett acceptdatum drar inte med sig ett "
          "giltig till (ägardirektiv 23 okt).")
    # 3. OCH SIDAN ÄR LADDBOXENS, RAD FÖR RAD, UTOM ACCEPTRADEN. Det är
    #    måttet som gör provfallet ofarligt: det kan inte visa ett tal eller
    #    en sträng som laddboxsidan inte redan visar.
    import difflib as _difflib
    def _utan_huvud(h):
        h = re.sub(r"<!-- BYGGD FIL.*?-->\n", "", h, flags=re.S)
        # KORTHOJDEN NORMALISERAS BORT, och det ar inte en uppmjukning.
        # Provfallets kort ar 1 250,8 px mot laddboxens 1 222,8: acceptraden
        # ar 28 px hog. Skillnaden ar alltsa en FOLJD av den enda mekanism
        # provfallet visar, inte en andra nyttolast, och kravet star kvar vid
        # TVA rader i stallet for att mjukas upp till fyra. Att provfallets
        # egen korthojd ar ratt provas av K-grinden, som tacker det ocksa.
        h = re.sub(r'(--oa-kort:\s*)[\d.]+px', r"\1DATA", h)
        return h.split("\n")
    _d = [l for l in _difflib.unified_diff(
            _utan_huvud((HAR / "fall" / "laddbox.html").read_text(encoding="utf-8")),
            _utan_huvud(_pf_h.read_text(encoding="utf-8")),
            "laddbox", PROVFALL, lineterm="", n=0)
          if l[:1] in "+-" and l[:3] not in ("+++", "---")]
    kolla(len(_d) == 2 and all('id="oaAccept"' in l for l in _d),
          "provfallet skiljer sig från fall/laddbox.html i %d rader, väntade 2 och bara "
          "acceptraden: %s" % (len(_d), [l.strip()[:80] for l in _d]))
    # 4. OCH DET BLANDAS INTE IN BLAND DE FEM. Ett provfall som räknas som
    #    ett sjätte fall är ett fall ingen granskat som ett fall.
    kolla(PROVFALL not in MALLAR, "provfallet står i MALLAR och räknas som en mall")


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
    # OCH PROVFALLET STÅR DÄR, MÄRKT SOM ETT PROV. En sida i fall/ som inte
    # står i översikten är en sida ägaren inte hittar, och ett provfall som
    # inte säger att det är ett prov läser som ett sjätte fall.
    kolla('href="prov-acceptdatum.html"' in _o,
          "fall/index.html länkar inte till provfallet för acceptdatumet")
    kolla("PROV." in _o and "provvärde" in _o,
          "fall/index.html säger inte att provfallet är ett prov med ett provvärde")


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

# WCAG AA, MÄTT I WEBBLÄSAREN OCH KÖRT HÄRIFRÅN.
# verktyg/kontrast.py fanns sedan tidigare men kördes bara för hand, och den
# returnerade dessutom alltid 0: en sida under kravet gav exit 0 och såg
# godkänd ut. Båda är stängda. Tre sidor räcker för att täcka VARJE yta i
# verktygets lista, och det är mätt och inte antaget: de fem sidorna har
# samma markup utanför stegen (3c ovan), och de tre ytor som bara finns på
# en sida är ingår-listan (service), "ingen kostnad nu" (laddbox) och
# acceptraden (provfallet). Unionen av deras tomma selektorer ska vara tom.
if "--snabb" not in sys.argv:
    import subprocess as _sp2
    _tomma = None
    for _sida in ("laddbox", "service", "prov-acceptdatum"):
        _r2 = _sp2.run([sys.executable, str(HAR / "verktyg" / "kontrast.py"),
                        str(HAR / "fall" / (_sida + ".html"))],
                       capture_output=True, text=True, cwd=str(HAR),
                       env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1"))
        kolla(_r2.returncode == 0,
              "kontrast %s: %s" % (_sida, " | ".join(l.strip() for l in _r2.stdout.split("\n")
                                                     if "UNDER" in l or "INGEN" in l)[:300]))
        _t = {l.split()[0] for l in _r2.stdout.split("\n") if "traffade inget" in l}
        _tomma = _t if _tomma is None else (_tomma & _t)
    kolla(not _tomma,
          "kontrast: selektorerna %s träffade ingen yta på någon av de tre sidorna. En "
          "mätning som letar efter borttagna ytor är lika grön som en som letar efter "
          "alla." % sorted(_tomma or []))

# VILLKOREN NÅR PAPPERET, ÄVEN MED FOLDEN STÄNGD.
# Ägarens dropdown skapade en ny felväg: en STÄNGD fold döljer sitt innehåll
# genom ::details-content med content-visibility:hidden, och det biter ingen
# display-regel på barnet. Offertrepot lärde sig det av en riktig
# utskrifts-PDF där villkoren saknades helt (gemensamt/system.css rad 505
# till 522). DET HÄR ÄR EN KÄLLKONTROLL, inte en mätning av papperet: den
# säger att de tre reglerna finns, inte att de verkar. Papperet är mätt för
# hand 25 oktober med en riktig utskrifts-PDF av fall/service.html, där
# folden står öppen och adressen skrivs ut efter länken.
_css = (HAR / "styles.css").read_text(encoding="utf-8")
_print = _css[_css.index("@media print"):] if "@media print" in _css else ""
for _regel, _varfor in (
        (".oa__fold::details-content", "folden öppnas inte på papper"),
        ("content-visibility:visible", "folden öppnas inte på papper"),
        (".oa__fold > .oa__fold-kropp{ display:block", "foldens kropp visas inte på papper"),
        ('.oa__fold a::after{ content:" (" attr(href)', "adressen skrivs inte ut efter länken")):
    kolla(_regel in _print,
          "styles.css @media print saknar %r: %s. Det som binder kunden ska med på papperet."
          % (_regel, _varfor))

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

# INVARIANT 3a. KORTHOJDEN I SIDAN AR SIDANS EGEN, OCH KAN INTE DRIFTA.
# styles.css fryser centreringen med
#   padding-top:max(husets padding, calc((100dvh - var(--oa-kort))/2))
# och --oa-kort bakas in per sida av bygg.py. Det talet ar den enda delen av
# rattningen som kan bli FEL i tysthet: andrar nagon kortets innehall utan
# att bygga om star en gammal korthojd kvar, och sidan centreras efter en
# sida som inte finns langre. Toppen STAR fortfarande still - skiftet ar 0,0
# for vilket konstant K som helst - men vilopositionen blir fel.
#
# GRINDEN MATER FARSKT genom bygg.mat_kort(), alltsa SAMMA funktion, samma
# Chrome och samma flaggor som bygget bakade med. Matte de pa tva olika satt
# vore skillnaden brus i stallet for ett prov.
#
# TOLERANSEN 0,5 PX, OCH DEN AR SKRIVEN FOR ATT DEN AR VALD:
# matskriptet bakar in med toFixed(1), sa 0,05 px avrundning ar inbyggd.
# 0,5 ar tio ganger det, och samtidigt langt under den minsta verkliga
# innehallsandringen - en listpunkt ar ~24 px, en textrad ~20 px - sa grinden
# slapper avrundning och fangar allt som ar en riktig andring. Uppmatt
# 31 oktober: samma sida matt tre ganger gav 0,00 px spridning, och alla sex
# sidorna matte +0,00 px mot sitt inbakade tal.
if "--snabb" not in sys.argv:
    import bygg as _bygg_k
    K_TOLERANS = 0.5
    for mall in MALLAR + ["prov-acceptdatum"]:
        _f = HAR / "fall" / (mall + ".html")
        if not _f.exists():
            kolla(False, "korthojd: %s saknas" % _f)
            continue
        _t = _f.read_text(encoding="utf-8")
        _m = re.search(r'<div class="oa"[^>]*style="[^"]*--oa-kort:\s*([\d.]+)px', _t)
        kolla(bool(_m),
              "korthojd: %s bar ingen --oa-kort. Utan den ar padding-top ogiltig vid "
              "berakningen och sidan tappar sin toppspalt helt." % mall)
        if not _m:
            continue
        _bakat = float(_m.group(1))
        _farskt = _bygg_k.mat_kort(_t, mall)
        kolla(abs(_farskt - _bakat) <= K_TOLERANS,
              "korthojd: %s bar --oa-kort %.1f px men kortet mater %.1f px (%+.2f, "
              "tolerans %.1f). Innehallet har andrats utan att sidan byggts om, och "
              "centreringen utgar fran en sida som inte finns langre. Kor python3 "
              "bygg.py." % (mall, _bakat, _farskt, _farskt - _bakat, K_TOLERANS))

# INVARIANT 3b. RORELSEN GAR AV NAR ANVANDAREN BETT OM DET - OCH PA NAR HAN
# INTE HAR. Raderna i styles.css rad 332 till 344 fanns redan; det har provet
# finns for att de BITER, matt pa den renderade sidan och inte last ur filen.
# TRE TILLSTAND, INTE TVA: provet kraver bade att de fyra rorelserna ar
# NAMNGIVNA och gar nar rorelse ar tillaten, och att de ar none nar den ar
# reducerad. Bara det forsta hade godkant en sida dar nagon rakat stanga av
# animationerna helt; bara det andra hade godkant en sida dar reduced-motion
# inte bet. Mats med verktyg/foldskifte.py, som ger getComputedStyle-varden.
if "--snabb" not in sys.argv:
    import subprocess as _sp2

    def _rorelse(extra):
        r = _sp2.run([sys.executable, str(HAR / "verktyg" / "foldskifte.py"),
                      "fall/laddbox.html", "1180", "1440"] + extra,
                     capture_output=True, text=True, cwd=str(HAR),
                     env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1"))
        if r.returncode != 0:
            return None
        return json.loads(r.stdout)["rorelse"]

    _pa = _rorelse(["--rorelse"])
    _av = _rorelse([])
    kolla(_pa is not None and _av is not None,
          "rorelse: foldskifte.py gav inga matvarden. Provet ar INTE kort.")
    if _pa and _av:
        kolla(_pa["reducerad"] is False and _av["reducerad"] is True,
              "rorelse: mediefragan svarade %r / %r, vantade False / True. Matningen "
              "provade inte de tva lagen." % (_pa["reducerad"], _av["reducerad"]))
        # MED RORELSE: alla fyra ska faktiskt ga.
        for _n, _vantat in (("disc", "oa-disc"), ("tick", "oa-tick"), ("halo", "oa-halo")):
            kolla(_pa[_n]["namn"] == _vantat and _pa[_n]["tid"] != "0s",
                  "rorelse: med rorelse tillaten heter %s:s animation %r pa %s. "
                  "Vantade %r. Nagon har stangt av den for alla."
                  % (_n, _pa[_n]["namn"], _pa[_n]["tid"], _vantat))
        kolla(_pa["pil"]["transition"] != "0s",
              "rorelse: foldpilens transition ar %s med rorelse tillaten."
              % _pa["pil"]["transition"])
        # REDUCERAD: alla fyra ska vara slackta.
        for _n in ("disc", "tick", "halo"):
            kolla(_av[_n]["namn"] == "none" and _av[_n]["tid"] == "0s",
                  "rorelse: med reducerad rorelse gar %s anda (%r, %s). Reglerna i "
                  "styles.css biter inte." % (_n, _av[_n]["namn"], _av[_n]["tid"]))
        kolla(_av["pil"]["transition"] == "0s",
              "rorelse: foldpilens transition ar %s med reducerad rorelse, vantade 0s."
              % _av["pil"]["transition"])

# INVARIANT 3c. DE FYRA SAKERNA MAPPAS FRAN KONTRAKTET TILL SIDAN.
# AGARENS ORD 31 oktober, ordagrant: "Sakerstall en sista gang att alla
# orderbekraftelser fungerar for alla mallar, sa ifall man valjer tillagg oso
# eller villkor sa mappas det korrekt, samma sak med kostnader som kan
# tillkomma & vad du behover gora innan."
# ordagrant.py provar LYDELSEN mot offertrepot. Det har provar VAGEN: att
# varje post kommer med, i kontraktets ordning, och att en fold utan innehall
# ar DOLD och inte en rubrik med tomhet under. Tva olika fel, tva olika prov.
# Den tredje delen RENDERAR en variant utan faltet, for att lasa en mall som
# redan har faltet bevisar ingenting om fallet dar det saknas; den gar darfor
# bara i den fulla korningen.
import mappning as _mappning
_m_antal, _m_fel = _mappning.kor(tyst=True, rendera_ocksa="--snabb" not in sys.argv)
for f in _m_fel:
    kolla(False, "mappning: " + f)
# GOLVET. En post som tas bort ur ett kontrakt tar sin kontroll med sig, och
# ett prov som ser mindre blir gronare. Talen ar UPPMATTA 31 oktober, inte
# gissade: 105 utan renderingarna, 135 med dem.
_m_golv = 105 if "--snabb" in sys.argv else 135
kolla(_m_antal >= _m_golv,
      "mappning: bara %d kontroller, vantade minst %d. Provet har krympt."
      % (_m_antal, _m_golv))
_mappning_kord = _m_antal

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
    # SKARMJAMFORELSEN KORS HAR, INTE BARA FOR HAND.
    # verktyg/jamfor-skarm.py matte glidningen mellan det har kortet och
    # offertrepots gemensamt/block/skarm-accept.html, och den var ROD fran
    # 25 oktober: acceptraden lades till utan en post i AVSIKT. Ingen sag
    # det, for maetaren kordes bara nar nagon rakade kora den. Ett orakel
    # som inte kors av prov.py ar ett orakel som inte finns.
    import subprocess as _sp
    _r = _sp.run([sys.executable, str(HAR / "verktyg" / "jamfor-skarm.py"), str(NORDSTJARNA)],
                 capture_output=True, text=True, cwd=str(HAR),
                 env=dict(__import__("os").environ, PYTHONDONTWRITEBYTECODE="1"))
    kolla(_r.returncode == 0,
          "jamfor-skarm: %s" % " | ".join(l.strip() for l in _r.stdout.split("\n")
                                          if l.strip().startswith(("+", "-", "0 ", "1 ", "2 "))
                                          or "OFÖRKLARAD" in l or "GLIDNING" in l)[:400])

    import talen as _talen
    _n, _felt, _rakn = _talen.kor(NORDSTJARNA, tyst=True)
    for f in _felt:
        kolla(False, "talen: " + f)
    # GOLVET 30 -> 44, 29 OKTOBER, OCH DET GICK VIA 28.
    # Golvet finns for att talprovet inte ska krympa i tysthet: en kontrakts-
    # post som tas bort tar sin kontroll med sig. Tva saker hande samma dag.
    # NED: agarordern tog bort stegremsan, och med den servicemallens tva tal
    # i steg 2 ("24 till 72 timmar"). Tva tal farre var alltsa ratt.
    # UPP: folden "Kostnader som kan tillkomma" kom till, och dess sexton
    # prissatta rader ar tal kunden ser. ogonfalt() raknade bara order och sag
    # dem inte; nu gor den det. Golvet star vid det faktiska talet, som det
    # gjorde nar det skrevs.
    kolla(_n >= 44, "talen: bara %d tal kontrollerade, väntade minst 44" % _n)
    kolla(_rakn["fil"] >= 20,
          "talen: bara %d operander slogs upp i offertrepots filer. Ett prov som bara "
          "jämför kontraktet mot sig självt är värdelöst." % _rakn["fil"])
    _talen_kord = (_n, _rakn)

print("%d kontroller" % kontroller)
print("mappning:  %d kontroller av tillagg, villkor, kostnader och forberedelser "
      "i fem mallar" % _mappning_kord)
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
