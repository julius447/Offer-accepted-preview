#!/usr/bin/env python3
"""Varje TAL på bekräftelsen, härlett ur offertrepots egna källfiler.

    python3 verktyg/talen.py ~/Desktop/"Claude Code"/laddboxoffert

LÄSER BARA. Skriver ingenting i det andra repot.

VARFÖR DEN FINNS. Ägarsvar 60, 25 oktober, på frågan "inget prov går tillbaka
till källan för talen": "Bygg det nu."

`verktyg/ordagrant.py` bevakar varje STRÄNG kunden ser. Talen hade inget
motsvarande. `prov.py` provar att sidans belopp står i kontraktet och att
kontraktets belopp står på sidan, men kontraktet är en KOPIA av offertens
sanning, och en kopia kan drifta utan att en enda kontroll blir röd. Det
provet säger alltså bara att sidan är lika med sig själv, ett led längre bort.

DÄRFÖR GÅR DEN HÄR FILEN TILL KÄLLFILEN. För varje tal i kontraktet finns en
HÄRLEDNING och en KÄLLA per operand, och oraklet

  1. slår upp varje operand i offertrepots fil, på plats, vid varje körning,
  2. räknar om uttrycket självt och jämför med kontraktets tal,
  3. kräver att filen ligger under MALLENS EGNA sökvägar, så en mall inte kan
     låna en annan malls pris (samma regel och samma skäl som ordagrant.py:
     "Driftsättning och avprovning" var en helt riktig rad, i fel mall),
  4. kräver en post för VARJE tal som når kundens öga, uppräknade ur datat.

Punkt 4 är poängen med punkt 4. En handskriven lista över vilka tal som ska
provas hade räknat upp precis de tal som redan var rätt, och en ny rad i en
offert hade kommit in utan källa och utan att något blivit rött. Oraklet
räknar därför upp fälten SJÄLVT ur kontraktet och kräver en post per fält.

ETT TAL I EN STRÄNG ÄR OCKSÅ ETT TAL. En sträng som ordagrant.py hittar i
offertrepot bär sina siffror med sig: hittas "24 till 72 timmar" ordagrant är
24 och 72 bevisade i samma slag. Men strängarna i `_undantag_ordagrant`
KOMPONERAS i körning och finns inte i någon fil, så deras siffror är obevisade.
Grannrabattens not säger "Upp till 1 500 kr av, 500 kr för varje granne", och
ingen kontroll band talet 1 500 till antalet inbjudna grannar. Nu gör en:
1 500 = 500 gånger 3, där 500 kommer ur laddboxmotorn och 3 ur radens egen
text. Byter någon texten till fyra grannar men glömmer noten blir provet rött.

KÄLLFORMERNA, tre stycken, plus två hänvisningar inom kontraktet:

  "fil#väg"            JSON. Vägen slås upp och värdet MÅSTE vara talet.
                       Vägsegment: punkt mellan nycklar, [fält=värde] väljer
                       posten i en lista ELLER nyckeln i ett objekt, och
                       "$nyckel" sist ger NYCKELN i stället för värdet (ett
                       paketpris som ÄR nyckeln i paket.json).
                       Är värdet en sträng ska talet stå i den.
  "fil@ankare"         Textfil. Talet ska stå som eget tal på en rad som också
                       bär ankaret. Ankaret krävs: ett löst tal någonstans i
                       en 900 rader lång fil bevisar ingenting.
  ".kontrakt.väg"      Ett annat tal i SAMMA kontrakt, som i sin tur måste ha
                       en egen post. Så binds totalen till sina rader och
                       radbeloppet till sitt antal.
  "val: <skäl>"        Kundens eget val (hur många spotlights). Det finns inte
                       i någon fil och ska inte låtsas göra det. Skälet är
                       obligatoriskt och syns i utskriften.

Varje operand som står FLERA gånger i uttrycket kräver en LISTA med en källa
per förekomst. Skälet står i batterifallet: "128126 - min(128126 // 2,
50000 * 2)" har två tvåor, och de betyder olika saker (grön tekniks halva och
antalet personer i hushållet). En delad källa hade påstått att de är samma.
"""
import ast
import json
import pathlib
import re
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HAR / "verktyg"))
import ordagrant as _ordagrant                                      # noqa: E402

MALLAR = _ordagrant.MALLAR
SOKVAGAR = _ordagrant.SOKVAGAR
FALT = _ordagrant.FALT


# ----------------------------------------------------------------- uttrycket
def rakna(uttryck):
    """(värdet, [literaler i ordning]). Bara aritmetik, aldrig eval().

    eval() på en sträng ur en datafil är en körväg från datalagret till
    skalet. Trädet gås igenom nod för nod och allt som inte är ett tal, en
    av de fyra räknesätten, min eller max avvisas."""
    literaler = []

    def ev(n):
        if isinstance(n, ast.Expression):
            return ev(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) \
                and not isinstance(n.value, bool):
            literaler.append(n.value)
            return n.value
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        if isinstance(n, ast.BinOp):
            a, b = ev(n.left), ev(n.right)
            for typ, f in ((ast.Add, lambda: a + b), (ast.Sub, lambda: a - b),
                           (ast.Mult, lambda: a * b), (ast.Div, lambda: a / b),
                           (ast.FloorDiv, lambda: a // b)):
                if isinstance(n.op, typ):
                    return f()
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) \
                and n.func.id in ("min", "max") and not n.keywords:
            arg = [ev(a) for a in n.args]
            return min(arg) if n.func.id == "min" else max(arg)
        raise ValueError("otillaten del i uttrycket: %s" % ast.dump(n))

    return ev(ast.parse(uttryck, mode="eval")), literaler


# ------------------------------------------------------------------- vägarna
def segment(vag):
    """'storlekar[kwh=20.0].brutto' -> [('nyckel','storlekar'),
    ('filter','kwh=20.0'), ('nyckel','brutto')]. Hakparentesen tas hel, så
    punkten i 20.0 inte delar vägen."""
    ut, i = [], 0
    while i < len(vag):
        if vag[i] == ".":
            i += 1
            continue
        if vag[i] == "[":
            j = vag.index("]", i)
            inne = vag[i + 1:j]
            # [0] ar ett LISTINDEX, [grupp=odrift] ar ett filter. Skilj pa dem:
            # utan den har raden last ".order.rader[0].belopp" som "posten i
            # listan vars falt '0' ar tomt", och ingen post matchade nagonsin.
            ut.append(("index", inne) if inne.lstrip("-").isdigit() and "=" not in inne
                      else ("filter", inne))
            i = j + 1
            continue
        j = i
        while j < len(vag) and vag[j] not in ".[":
            j += 1
        ut.append(("nyckel", vag[i:j]))
        i = j
    return ut


def _lika(a, b):
    """Jämför ett värde ur en fil med ett värde ur en väg. 20 och '20.0' är
    samma tal; 'Premium' och 'premium' är inte samma namn."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return str(a) == str(b)


def slag_upp(data, vag):
    """Värdet på `vag` i `data`, eller ett ValueError som säger var det tog slut."""
    nuvarande, gangen = data, ""
    ta_nyckel = False
    delar = segment(vag)
    if delar and delar[-1] == ("nyckel", "$nyckel"):
        ta_nyckel, delar = True, delar[:-1]
    for sort, text in delar:
        gangen += ("." if gangen else "") + text
        if sort == "index":
            if not isinstance(nuvarande, list):
                raise ValueError("[%s] ar ett listindex men %r ar ingen lista"
                                 % (text, gangen))
            if not -len(nuvarande) <= int(text) < len(nuvarande):
                raise ValueError("listan pa %r har %d poster, inte index %s"
                                 % (gangen, len(nuvarande), text))
            nuvarande = nuvarande[int(text)]
            continue
        if sort == "nyckel":
            if isinstance(nuvarande, list) and re.fullmatch(r"-?\d+", text):
                nuvarande = nuvarande[int(text)]
                continue
            if not isinstance(nuvarande, dict) or text not in nuvarande:
                raise ValueError("vagen tar slut vid %r" % gangen)
            nuvarande = nuvarande[text]
            continue
        falt, _, varde = text.partition("=")
        if isinstance(nuvarande, list):
            poster = [(None, p) for p in nuvarande if isinstance(p, dict)]
        elif isinstance(nuvarande, dict):
            poster = [(k, v) for k, v in nuvarande.items()
                      if isinstance(v, dict) and not k.startswith("_")]
        else:
            raise ValueError("[%s] gar inte att filtrera pa %r" % (text, type(nuvarande).__name__))
        traff = [(k, v) for k, v in poster if falt in v and _lika(v[falt], varde)]
        if len(traff) != 1:
            raise ValueError("[%s] traffade %d poster, ska traffa exakt 1" % (text, len(traff)))
        nyckel, nuvarande = traff[0]
        if ta_nyckel and (sort, text) == delar[-1]:
            if nyckel is None:
                raise ValueError("$nyckel pa en lista: listposter har ingen nyckel")
            return nyckel
    if ta_nyckel:
        raise ValueError("$nyckel maste sta sist efter ett [falt=varde] i ett objekt")
    return nuvarande


# ----------------------------------------------------------------- källorna
def tecken(tal):
    """Talet som det skrivs. int-flyttal skrivs utan decimal: 20.0 är 20."""
    if isinstance(tal, float) and tal == int(tal):
        return str(int(tal))
    return repr(tal) if isinstance(tal, float) else str(tal)


def _fristaende(tal, text):
    """Står talet som ett eget tal i texten?

    Fyra saker får det INTE vara, och alla fyra har bitit:
      * en siffra i ett ord: 3:an i "SAJ HS3" är inte talet tre,
      * en bit av ett längre tal: 2:an i 128126,
      * heltalsdelen av ett decimaltal: 20 i 20.5,
      * en grupp i ett avgränsat tal: 1 i "1,500".
    Men ett tal FÅR följas av komma och mellanslag, för så ser kod ut:
    `min(brutto // 2, pott)`. Den första versionen av den här raden avvisade
    varje efterföljande komma och hittade därför inte en enda operand i en
    Python-fil."""
    t = re.escape(tecken(tal))
    return re.search(r"(?<![\w.])(?<!,)%s(?![\w])(?!\.\d)(?!,\d)" % t, text) is not None


def kolla_kalla(tal, kalla, mall, repo, kontrakt, fel, vag):
    """Ett operand mot sin källa. Lägger fel i `fel` och returnerar
    ('fil'|'kontrakt'|'val', beskrivning) för räkningen."""
    if kalla.startswith("val:"):
        if not kalla[4:].strip():
            fel.append("%s: %s operanden %s ar 'val:' utan skal. Ett val utan "
                       "skal ar ett pahittat tal." % (mall, vag, tal))
        return "val", kalla

    if kalla.startswith("."):
        # En hanvisning kan peka pa ett tal INNE i en strang: ".order.
        # utestaende[0].text#3" ar trean i "Grannrabatt, 3 grannar inbjudna".
        bas, _, i_strang = kalla.partition("#")
        try:
            v = slag_upp(kontrakt, bas)
        except (ValueError, IndexError, KeyError) as e:
            fel.append("%s: %s operanden %s pekar pa %s i kontraktet, men %s"
                       % (mall, vag, tal, kalla, e))
            return "kontrakt", kalla
        if i_strang:
            if not isinstance(v, str) or int(i_strang) not in _tal_i_strang(v):
                fel.append("%s: %s operanden %s pekar pa talet %s i %s, men det talet "
                           "star inte i strangen %r" % (mall, vag, tal, i_strang, bas, v))
            elif not _lika(float(i_strang), tal):
                fel.append("%s: %s operanden %s pekar pa %s. Talen har glidit isar."
                           % (mall, vag, tal, kalla))
            return "kontrakt", kalla
        if not _lika(v, tal):
            fel.append("%s: %s operanden %s ska vara %s enligt kontraktets egen %s. "
                       "Talen har glidit isar inne i kontraktet."
                       % (mall, vag, tal, v, kalla))
        return "kontrakt", kalla

    if "#" in kalla:
        filnamn, _, inre = kalla.partition("#")
    elif "@" in kalla:
        filnamn, _, inre = kalla.partition("@")
    else:
        fel.append("%s: %s kallan %r saknar # eller @. En fil utan vag eller "
                   "ankare bevisar ingenting." % (mall, vag, kalla))
        return "fil", kalla

    if not any(filnamn == v or filnamn.startswith(v) for v in SOKVAGAR[mall]):
        fel.append("%s: %s kallan ligger i %s, utanfor mallens egna sokvagar %s. "
                   "En mall far inte lana en annan malls pris."
                   % (mall, vag, filnamn, SOKVAGAR[mall]))
        return "fil", kalla
    p = repo / filnamn
    if not p.exists():
        fel.append("%s: %s kallan %s finns inte i offertrepot. Filen har flyttat "
                   "eller bytt namn, och talet star utan tacknng." % (mall, vag, filnamn))
        return "fil", kalla

    if "#" in kalla:
        try:
            v = slag_upp(json.loads(p.read_text(encoding="utf-8")), inre)
        except json.JSONDecodeError as e:
            fel.append("%s: %s kallan %s gar inte att lasa som JSON: %s" % (mall, vag, filnamn, e))
            return "fil", kalla
        except (ValueError, IndexError, KeyError) as e:
            fel.append("%s: %s operanden %s sokte %s i %s, men %s. Kallan har "
                       "flyttat sig." % (mall, vag, tal, inre, filnamn, e))
            return "fil", kalla
        if isinstance(v, str):
            if not _fristaende(tal, v):
                fel.append("%s: %s operanden %s star inte i strangen %r pa %s i %s"
                           % (mall, vag, tal, v[:60], inre, filnamn))
        elif not _lika(v, tal):
            fel.append("%s: %s operanden %s, men %s i %s sager %r. Kallan har andrats "
                       "och kontraktet bar det gamla talet." % (mall, vag, tal, inre, filnamn, v))
        return "fil", kalla

    rader = [r for r in p.read_text(encoding="utf-8").split("\n") if inre in r]
    if not rader:
        fel.append("%s: %s ankaret %r finns inte i %s. Raden har skrivits om, och "
                   "talet %s har ingen kalla langre." % (mall, vag, inre, filnamn, tal))
    elif not any(_fristaende(tal, r) for r in rader):
        fel.append("%s: %s talet %s star inte pa nagon av de %d rader i %s som bar "
                   "ankaret %r. Kallan sager nu nagot annat."
                   % (mall, vag, tal, len(rader), filnamn, inre))
    return "fil", kalla


# ------------------------------------------------------- talen som når ögat
def _tal_i_strang(s):
    """Varje fristående tal i en kundsträng, som kunden läser det.

    'Upp till 1 500 kr' ger 1500 (hårdspatien är en avgränsare, inte ett
    mellanrum mellan två tal), 'SAJ HS3' ger ingenting, '5-pack' ger 5."""
    ut = []
    for m in re.finditer(r"(?<![\w.,])\d[\d  ]*(?![\w])", s):
        t = m.group(0).replace(" ", "").replace(" ", "")
        if t.isdigit():
            ut.append(int(t))
    return ut


def ogonfalt(kontrakt):
    """[(väg, tal, sort)] för VARJE tal kunden kan se, uppräknat ur datat.

    Uppräknat, inte listat: en ny rad i en offert får en ny väg här utan att
    någon skriver en rad kod, och saknar den källa blir provet rött."""
    ut = []
    o = kontrakt.get("order") or {}
    if isinstance(o.get("total"), (int, float)):
        ut.append((".order.total", o["total"], "belopp"))
    p = o.get("paket")
    if isinstance(p, dict) and isinstance(p.get("belopp"), (int, float)):
        ut.append((".order.paket.belopp", p["belopp"], "belopp"))
    for i, r in enumerate(o.get("rader") or []):
        if not isinstance(r, dict):
            continue
        if isinstance(r.get("belopp"), (int, float)):
            ut.append((".order.rader[%d].belopp" % i, r["belopp"], "belopp"))
        # ANTAL OCH STYCKPRIS RENDERAS BARA NAR ANTAL > 1 (script.js: "6
        # stycken, 800 kr per styck"). Ett antal som ar 1 nar aldrig ogat och
        # kravs darfor inte; ett som ar 2 gor det.
        if isinstance(r.get("antal"), int) and r["antal"] > 1:
            ut.append((".order.rader[%d].antal" % i, r["antal"], "antal"))
            if isinstance(r.get("styckpris"), (int, float)):
                ut.append((".order.rader[%d].styckpris" % i, r["styckpris"], "belopp"))
    # KOSTNADER SOM KAN TILLKOMMA, 29 oktober. Folden kom till samma dag, och
    # dess prissatta rader ar TAL KUNDEN SER: "245 kr per meter" star i samma
    # fold som "850 kr per paborjad timme". Walkern raknade bara order, sa de
    # sexton beloppen hade stat obevakade medan allt annat pa sidan har en
    # kalla. Forsta versionen lade talet i ett TEXT-falt, och da provades ett
    # pris som om det vore copy; ordagrant.py sag det direkt. Raden bar nu ett
    # belopp och en enhet var for sig, och beloppet hor hit.
    # Elcentralens tre rader har belopp null (villkorstexter utan pris) och
    # far darfor ingen vag, vilket ar ratt: det finns inget tal att bevaka.
    for i, r in enumerate(kontrakt.get("kostnader") or []):
        if isinstance(r, dict) and isinstance(r.get("belopp"), (int, float)):
            ut.append((".kostnader[%d].belopp" % i, r["belopp"], "belopp"))

    # TALEN INNE I DE KOMPONERADE STRANGARNA. En sträng som ordagrant.py
    # hittar ordagrant i offertrepot bar sina siffror med sig. En sträng i
    # _undantag_ordagrant finns inte i nagon fil, och da gor inte dess
    # siffror det heller.
    undantag = kontrakt.get("_undantag_ordagrant") or {}
    for vag, s in _ordagrant.strangar(kontrakt):
        if vag not in undantag:
            continue
        for t in _tal_i_strang(s):
            ut.append(("%s#%d" % (vag, t), t, "strang"))
    return ut


# --------------------------------------------------------------------- körningen
def kor(repo, tyst=False, exempel=None):
    """(antal kontrollerade tal, [fel], raekningen) mot offertrepot i `repo`.

    `exempel` pekar pa en annan katalog med kontrakt an exempel/. Den finns
    for sjalvprovet nedan, som mutererar en KOPIA: oraklet maste kunna visas
    falla, och ett orakel som bara kan koras mot de riktiga filerna kan bara
    visas vara gront."""
    exempel = exempel or (HAR / "exempel")
    fel, antal, raknade = [], 0, {"fil": 0, "kontrakt": 0, "val": 0}
    if not (repo / "katalog" / "tillval.json").exists():
        return 0, ["%s ser inte ut som offertrepot: katalog/tillval.json saknas" % repo], raknade

    for mall in MALLAR:
        k = json.loads((exempel / (mall + ".json")).read_text(encoding="utf-8"))
        # Nycklar som borjar med _ ar noter, inte tal. Samma regel som
        # ordagrant.py:strangar foljer i kontraktet i ovrigt.
        poster = {n: v for n, v in (k.get("_tal") or {}).items() if not n.startswith("_")}
        vagar = ogonfalt(k)
        kanda = {v for v, _, _ in vagar}
        for extra in sorted(set(poster) - kanda):
            fel.append("%s: _tal har %s, men det talet finns inte i kontraktet. "
                       "En post som bevakar ett borttaget tal stoppar nasta andring, "
                       "inte nasta fel." % (mall, extra))
        for vag, tal, sort in vagar:
            antal += 1
            post = poster.get(vag)
            if not isinstance(post, dict):
                fel.append("%s: talet %s pa %s saknar post i _tal. Varje tal kunden ser "
                           "ska ga att folja till offertrepot." % (mall, tal, vag))
                continue
            uttryck, kallor = post.get("uttryck"), post.get("kallor") or {}
            if not isinstance(uttryck, str) or not uttryck.strip():
                fel.append("%s: %s saknar uttryck" % (mall, vag))
                continue
            try:
                varde, literaler = rakna(uttryck)
            except (ValueError, SyntaxError) as e:
                fel.append("%s: %s uttrycket %r gar inte att rakna: %s" % (mall, vag, uttryck, e))
                continue
            if not _lika(varde, tal):
                fel.append("%s: %s star som %s men harledningen %s ger %s. Kontraktet och "
                           "dess egen harledning sager olika." % (mall, vag, tal, uttryck, varde))
            # Varje literal har en kalla, varje kalla har en literal.
            behov = {}
            for lit in literaler:
                behov[tecken(lit)] = behov.get(tecken(lit), 0) + 1
            for namn in sorted(set(kallor) - set(behov)):
                fel.append("%s: %s har en kalla for %s, men talet star inte i uttrycket %r"
                           % (mall, vag, namn, uttryck))
            for namn, n in sorted(behov.items()):
                if namn not in kallor:
                    fel.append("%s: %s operanden %s i %r saknar kalla. Ett tal utan kalla "
                               "ar en bugg, inte en smaksak." % (mall, vag, namn, uttryck))
                    continue
                v = kallor[namn]
                if n > 1 and not isinstance(v, list):
                    fel.append("%s: %s operanden %s star %d ganger i uttrycket och kraver "
                               "en LISTA med en kalla per forekomst: samma siffra pa tva "
                               "platser betyder sallan samma sak." % (mall, vag, namn, n))
                    continue
                lista = v if isinstance(v, list) else [v]
                if len(lista) != n:
                    fel.append("%s: %s operanden %s star %d ganger men har %d kallor"
                               % (mall, vag, namn, n, len(lista)))
                    continue
                for kalla in lista:
                    hur, _ = kolla_kalla(float(namn), kalla, mall, repo, k, fel, vag)
                    raknade[hur] += 1
                    # En hanvisning inom kontraktet ar bara ett bevis om den
                    # den pekar pa sjalv ar bevisad. Annars ar kedjan en ring.
                    if hur == "kontrakt" and kalla not in poster and kalla not in kanda:
                        fel.append("%s: %s pekar pa %s, som varken har en egen post i _tal "
                                   "eller ar ett tal kunden ser. Kedjan tar slut i luften."
                                   % (mall, vag, kalla))
            # En andra, oberoende kalla som ska ge samma tal.
            for kalla in post.get("och_samma_som") or []:
                kolla_kalla(tal, kalla, mall, repo, k, fel, vag + " (andra kallan)")
                raknade["fil"] += 1
            if not tyst and sort == "strang":
                print("   %-9s %-34s %s" % (mall, vag, uttryck))
    return antal, fel, raknade


# --------------------------------------------------- att oraklet faktiskt faller
# "Misstank ett gront prov pa nagot du inte sjalv sett fungera." De fem
# mutationerna nedan ar de fem satten talen kan ljuga pa, och var och en ska
# ge ett rott prov. Kor med --sjalvprov. INGENTING SKRIVS I OFFERTREPOT:
# bada sidor muteras i en kopia under /tmp.
MUTATIONER = [
    ("ett belopp i kontraktet andras utan att harledningen foljer med",
     "kontrakt", "laddbox", lambda d: d["order"].update(total=d["order"]["total"] + 1),
     "harledningen"),
    ("en post i _tal tas bort",
     "kontrakt", "elcentral", lambda d: d["_tal"].pop(".order.paket.belopp"),
     "saknar post i _tal"),
    # VANT 25 OKTOBER, INTE RADERAT. Mutationen hette "texten sager fyra
    # grannar men noten star kvar pa 1 500 kr" och vantade felet
    # "star inte i strangen": posten .order.utestaende[0].not#1500 band taket
    # till antalet inbjudna, och en text som sa fyra gjorde provet rott.
    # Agaren tog bort hela noten 25 oktober ("Har vill jag att vi anvander
    # foljande ENBART"), och med strangen gick dess tva poster i _tal.
    # Mutationen star kvar for att trean i RADENS egen text fortfarande ar
    # ett tal kunden ser och fortfarande maste ha en kalla: byts den till
    # fyra blir posten for trean foraldralos och fyran saknar post. Det ar
    # samma sanning en vaning ner, och att radera mutationen hade varit att
    # sluta prova den.
    ("antalet grannar i radens text andras utan att kallan foljer med",
     "kontrakt", "laddbox",
     lambda d: d["order"]["utestaende"][0].update(text="Grannrabatt, 4 grannar inbjudna"),
     "finns inte i kontraktet"),
    ("en ny rad laggs till i en offert utan att nagon skriver en kalla",
     "kontrakt", "service",
     lambda d: d["order"]["rader"].append({"typ": "tillagg", "namn": "Ny rad", "variant": None,
                                           "antal": 1, "styckpris": None, "belopp": 1, "avdrag": "rot"}),
     "saknar post i _tal"),
    ("priset i offertrepots katalog andras",
     "kalla", "katalog/tillval.json", lambda s: s.replace('"styckpris": 800', '"styckpris": 900'),
     "sager"),
    ("raden med BAS skrivs om i offertrepots laddboxmotor",
     "kalla", "offerter/laddbox/skript.js", lambda s: s.replace("var BAS=4450;", "var GRUND=4450;"),
     "ankaret"),
]


def sjalvprov(repo):
    """[(namn, foll den, varfor)] for varje mutation."""
    import shutil
    import tempfile
    ut = []
    # Varje fil nagon kalla pekar pa, plus den fil som avgor att repot ar repot.
    noder = {"katalog/tillval.json"}
    for mall in MALLAR:
        d = json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8"))
        for post in (d.get("_tal") or {}).values():
            if not isinstance(post, dict):
                continue
            for v in list((post.get("kallor") or {}).values()) + list(post.get("och_samma_som") or []):
                for kalla in (v if isinstance(v, list) else [v]):
                    if not kalla.startswith(".") and not kalla.startswith("val:"):
                        noder.add(re.split(r"[#@]", kalla, maxsplit=1)[0])
    for namn, sort, mal, andra, vantat in MUTATIONER:
        with tempfile.TemporaryDirectory(prefix="oa-talen-") as d:
            tmp = pathlib.Path(d)
            (tmp / "repo").mkdir()
            for n in noder:
                (tmp / "repo" / n).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(repo / n, tmp / "repo" / n)
            shutil.copytree(HAR / "exempel", tmp / "exempel")
            if sort == "kontrakt":
                f = tmp / "exempel" / (mal + ".json")
                k = json.loads(f.read_text(encoding="utf-8"))
                andra(k)
                f.write_text(json.dumps(k, ensure_ascii=False, indent=2), encoding="utf-8")
            else:
                f = tmp / "repo" / mal
                fore = f.read_text(encoding="utf-8")
                efter = andra(fore)
                if efter == fore:
                    ut.append((namn, False, "mutationen andrade ingenting i %s" % mal))
                    continue
                f.write_text(efter, encoding="utf-8")
            _, fel, _ = kor(tmp / "repo", tyst=True, exempel=tmp / "exempel")
            traff = [x for x in fel if vantat in x]
            ut.append((namn, bool(traff), (traff[0] if traff else
                       ("INGET FEL ALLS" if not fel else "fel, men inte om %r: %s" % (vantat, fel[0])))))
    return ut


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    rot = pathlib.Path(sys.argv[1]).expanduser().resolve()
    if not rot.exists():
        raise SystemExit("hittar inte " + str(rot))
    print("Nordstjarnan: %s\n" % rot)
    if "--sjalvprov" in sys.argv:
        trasigt = 0
        for namn, foll, varfor in sjalvprov(rot):
            print("  %-4s %-62s %s" % ("ROTT" if foll else "MISS", namn,
                                       (" ".join(varfor.split()))[:110]))
            trasigt += 0 if foll else 1
        print("\n%d mutationer, %d slapp forbi" % (len(MUTATIONER), trasigt))
        sys.exit(1 if trasigt else 0)
    n, f, r = kor(rot)
    print("\n%d tal kontrollerade: %d operander mot offertrepots filer, "
          "%d mot kontraktets egna tal, %d kundval" % (n, r["fil"], r["kontrakt"], r["val"]))
    for rad in f:
        print("  * " + rad)
    sys.exit(1 if f else 0)
