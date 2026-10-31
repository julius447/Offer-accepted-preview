#!/usr/bin/env python3
"""Fyra saker ur kontraktet, hela vagen till kundens oga, i alla fem mallarna.

    python3 verktyg/mappning.py
    python3 verktyg/mappning.py --sjalvprov    # att provet kan falla

AGARENS ORD 31 oktober, ordagrant: "Sakerstall en sista gang att alla
orderbekraftelser fungerar for alla mallar, sa ifall man valjer tillagg oso
eller villkor sa mappas det korrekt, samma sak med kostnader som kan
tillkomma & vad du behover gora innan."

DE FYRA SAKERNA, och var och en mats pa TRE satt:
  tillagg        order.rader  -> raderna i #oaRader
  villkor        offert.villkor_url -> href i #oaVillkorKropp
  kostnader      kostnader    -> posterna i #oaKostnaderKropp
  forberedelser  forberedelser -> punkterna i #oaForberedKropp

  1. ANTALET. Lika manga poster pa sidan som i kontraktet. En post som tappas
     tyst ar den defekt som inte syns: sidan ser hel ut och saknar en rad.
  2. ORDNINGEN. Posterna star i kontraktets ordning, inte i nagon annan.
     Kostnadsfolden ar en prislista; en omkastad prislista ar ett annat pris.
  3. DEN TOMMA SEKTIONEN AR DOLD, INTE TOM. KONTRAKT.md: saknas faltet ska
     folden "visas inte alls". Det mats genom att faltet FAKTISKT tas bort ur
     kontraktet och sidan renderas om, inte genom att lasa markupen i en mall
     som redan har faltet. Ett prov som bara laser den byggda sidan kan inte
     se vad som hander nar faltet saknas.

PROV 3 AR DET SOM KRAVER EN RENDERING. De tva forsta laser fall/<mall>.html,
som ar den sida kunden far. Det tredje bygger en variant genom samma
renderare som bygg.py, for annars provas en pastaende och inte en sida.

ordagrant.py provar LYDELSEN mot offertrepot. Den har provar VAGEN: att varje
post kommer med, i ordning, och att en fold utan innehall inte star kvar som
en rubrik med tomhet under. Tva olika fel, tva olika prov.
"""
import json
import pathlib
import re
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HAR))
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]

fel = []
kontroller = 0


def kolla(ok, text):
    global kontroller
    kontroller += 1
    if not ok:
        fel.append(text)


def avkoda(s):
    """Markupens text som en strang. &nbsp; blir hardspatie, inte spatie:
    huset kraver hardspatie i tusental, sa de tva ar OLIKA strangar."""
    return (s.replace("&nbsp;", " ").replace("&amp;", "&")
             .replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"'))


def taggbort(s):
    return avkoda(re.sub(r"<[^>]+>", "", s)).strip()


def sektion(html, _id):
    """(attributen, innehallet) for <section id=...> eller None."""
    m = re.search(r'<section[^>]*id="%s"([^>]*)>' % _id, html)
    if not m:
        return None
    # Sektionerna ar inte nastlade i den har sidan: ta till nasta </section>.
    slut = html.find("</section>", m.end())
    return (m.group(1), html[m.end():slut if slut > 0 else len(html)])


def kropp(html, _id):
    """Foldkroppens innehall. INGEN nastlad <div> finns i de tre kropparna
    (bara p/ul/li/b/span/a, se script.js rad 459 till 511), sa forsta
    </div> ar den ratta. Forsta versionen gick pa djupet och slaktade sista
    taggen: lanktexten las som 'Las vara kopvillkor</p' och provet blev rott
    om en sida som var hel. Ett matfel, inte ett fynd."""
    m = re.search(r'<div class="oa__fold-kropp" id="%s">(.*?)</div>' % _id, html, re.S)
    return m.group(1) if m else None


# ---------------------------------------------------------------- 1 och 2
def mat(mall, d=None, html=None, skriv=True):
    if d is None:
        d = json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8"))
    if html is None:
        html = (HAR / "fall" / (mall + ".html")).read_text(encoding="utf-8")
    rapport = []

    # --- TILLAGG: order.rader -> #oaRader ---------------------------------
    o = d.get("order") or {}
    rader = o.get("rader") or []
    # VAD SIDANS LISTA FAKTISKT AR, last ur script.js och inte antaget:
    # paketet forst NAR DET FINNS, sedan order.rader i ordning, sedan
    # order.utestaende. Service och tillagg har paket=null, och servicens
    # rader[0] bar typ="huvud": den ar huvudraden OCH en post i rader.
    # Forsta versionen av det har provet antog att huvudraden alltid lag
    # UTANFOR rader och rapporterade fyra falska fel pa tre hela mallar.
    vantat = []
    if (o.get("paket") or {}).get("namn"):
        vantat.append(("paket", o["paket"]["namn"]))
    for r in rader:
        vantat.append(("rader/" + str(r.get("typ")), r.get("namn")))
    for u in (o.get("utestaende") or []):
        vantat.append(("utestaende", u.get("text") or u.get("namn")))
    m = re.search(r'<ul class="oa__rader" id="oaRader"[^>]*>(.*?)</ul>', html, re.S)
    li = re.findall(r'<li class="oa__rad[^"]*">(.*?)</li>', m.group(1), re.S) if m else []
    kolla(len(li) == len(vantat),
          "%s: RADERNA. kontraktet ger %d rader (paket %s + order.rader %d + "
          "utestaende %d), sidan visar %d."
          % (mall, len(vantat), "1" if (o.get("paket") or {}).get("namn") else "0",
             len(rader), len(o.get("utestaende") or []), len(li)))
    for i, (varifran, namn) in enumerate(vantat):
        if i >= len(li):
            break
        text = taggbort(re.search(r'<span class="oa__rad-text">(.*?)</span>',
                                  li[i], re.S).group(1))
        kolla(namn and namn in text,
              "%s: RAD %d (%s). kontraktet sager %r, sidan sager %r. Ordningen "
              "eller posten stammer inte." % (mall, i, varifran, namn, text[:70]))
    antal_tillagg = sum(1 for r in rader if r.get("typ") == "tillagg")
    rapport.append(("rader (varav tillagg)", len(vantat), len(li),
                    "%d av order.rader har typ=tillagg" % antal_tillagg))

    # --- KOSTNADER: kostnader -> #oaKostnaderKropp ------------------------
    k = d.get("kostnader") or []
    sek = sektion(html, "oaKostnader")
    dold = bool(sek) and "hidden" in sek[0]
    kolla(bool(sek) and dold != bool(k),
          "%s: KOSTNADER. sektionen ar %s men kontraktet %s faltet."
          % (mall, "dold" if dold else "synlig", "har" if k else "saknar"))
    kr = kropp(html, "oaKostnaderKropp") or ""
    # TVA FORMER (script.js rad 476 till 481): prissatt rad <li>, och
    # villkorstext <li class="oa__fold-villkor">. Elcentralens tre rader ar
    # den andra sorten. Forsta versionen sokte bara "<li>" och rapporterade
    # elcentralens fold som TOM fastan den bar tre poster.
    poster = re.findall(r"<li[^>]*>(.*?)</li>", kr, re.S)
    kolla(len(poster) == len(k),
          "%s: KOSTNADER. kontraktet har %d poster, folden visar %d."
          % (mall, len(k), len(poster)))
    for i, p in enumerate(k):
        if i >= len(poster):
            break
        namn = taggbort(re.search(r"<b>(.*?)</b>", poster[i], re.S).group(1))
        kolla(namn == p["namn"],
              "%s: KOSTNADER post %d. kontraktet sager %r, folden sager %r."
              % (mall, i, p["namn"], namn))
    # Ingressen och finstilten syns PRECIS nar kontraktet bar dem.
    for falt, klass in (("kostnader_ingress", "oa__fold-intro"),
                        ("kostnader_fot", "oa__fold-fot")):
        har_sida = ('class="%s"' % klass) in kr
        kolla(har_sida == bool(d.get(falt)),
              "%s: KOSTNADER. %s star %s pa sidan men kontraktet %s den."
              % (mall, falt, "" if har_sida else "inte", "har" if d.get(falt) else "saknar"))
    rapport.append(("kostnader", len(k), len(poster),
                    "dold" if dold else "synlig"))

    # --- FORBEREDELSER: forberedelser -> #oaForberedKropp -----------------
    f = d.get("forberedelser") or []
    sek = sektion(html, "oaForbered")
    dold = bool(sek) and "hidden" in sek[0]
    kolla(bool(sek) and dold != bool(f),
          "%s: FORBEREDELSER. sektionen ar %s men kontraktet %s faltet."
          % (mall, "dold" if dold else "synlig", "har" if f else "saknar"))
    fk = kropp(html, "oaForberedKropp") or ""
    punkter = [taggbort(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", fk, re.S)]
    kolla(len(punkter) == len(f),
          "%s: FORBEREDELSER. kontraktet har %d punkter, folden visar %d."
          % (mall, len(f), len(punkter)))
    for i, p in enumerate(f):
        if i >= len(punkter):
            break
        kolla(punkter[i] == p,
              "%s: FORBEREDELSER punkt %d. kontraktet sager %r, folden sager %r."
              % (mall, i, p[:60], punkter[i][:60]))
    rapport.append(("forberedelser", len(f), len(punkter),
                    "dold" if dold else "synlig"))

    # --- VILLKOR: offert.villkor_url -> #oaVillkorKropp -------------------
    url = (d.get("offert") or {}).get("villkor_url")
    sek = sektion(html, "oaVillkor")
    dold = bool(sek) and "hidden" in sek[0]
    kolla(bool(sek) and dold != bool(url),
          "%s: VILLKOR. sektionen ar %s men kontraktet %s villkor_url."
          % (mall, "dold" if dold else "synlig", "har" if url else "saknar"))
    vk = kropp(html, "oaVillkorKropp") or ""
    href = re.search(r'href="([^"]*)"', vk)
    kolla(bool(url) == bool(href) and (not url or href.group(1) == url),
          "%s: VILLKOR. kontraktet sager villkor_url=%r, folden lankar till %r."
          % (mall, url, href.group(1) if href else None))
    kolla('href=""' not in vk,
          "%s: VILLKOR. folden bar ett TOMT href. Aldrig en lank som inte gar nagonstans."
          % mall)
    kolla(taggbort(vk) in ("", "Läs våra köpvillkor"),
          "%s: VILLKOR. lanktexten ar %r, vantade 'Läs våra köpvillkor'. "
          "Lydelsen ar offertens egen, ordagrant." % (mall, taggbort(vk)))
    rapport.append(("villkor", 1 if url else 0, 1 if href else 0,
                    "dold" if dold else "synlig"))

    if skriv:
        print("  %-10s %-15s %-9s %-7s %s" % (mall, "", "kontrakt", "sidan", ""))
        for namn, a, b, extra in rapport:
            flagga = "" if a == b else "   <-- SKILJER"
            print("  %-10s %-15s %8d %8d   %s%s" % ("", namn, a, b, extra, flagga))
    return d


# ---------------------------------------------------------------- 3
def tomma_sektioner(tyst=False):
    """DEN TOMMA SEKTIONEN AR DOLD, INTE TOM - matt genom en RENDERING.
    Faltet tas bort ur kontraktet och sidan byggs om. Att lasa en mall som
    redan har faltet bevisar ingenting om fallet dar det saknas."""
    import bygg
    tmp = HAR / "exempel" / ("_mapp-%d.json" % __import__("time").time_ns())
    try:
        for mall in MALLAR:
            d0 = json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8"))
            for falt, _id in (("kostnader", "oaKostnader"),
                              ("forberedelser", "oaForbered")):
                d = json.loads(json.dumps(d0))
                d.pop(falt, None)
                tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
                h = bygg.rendera(tmp)
                sek = sektion(h, _id)
                kolla(bool(sek) and "hidden" in sek[0],
                      "%s: utan %s star sektionen %s KVAR SYNLIG. En rubrik som lovar "
                      "innehall som inte finns ar varre an ingen rubrik." % (mall, falt, _id))
                # Och den ar dold, inte bara tom: ingen rubriktext far na kunden.
                kolla(bool(sek) and not re.search(r"<li[^>]*>", sek[1] or ""),
                      "%s: utan %s star det andå poster i %s." % (mall, falt, _id))
            # VILLKOR: utan url ska folden vara dold OCH utan tomt href.
            d = json.loads(json.dumps(d0))
            d["offert"].pop("villkor_url", None)
            tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            h = bygg.rendera(tmp)
            sek = sektion(h, "oaVillkor")
            kolla(bool(sek) and "hidden" in sek[0],
                  "%s: utan villkor_url star villkorsfolden KVAR SYNLIG." % mall)
            kolla('href=""' not in (sek[1] if sek else ""),
                  "%s: utan villkor_url renderades ett TOMT href." % mall)
            if not tyst:
                print("  %-10s utan kostnader / forberedelser / villkor_url: "
                      "dold, dold, dold" % mall)
    finally:
        tmp.unlink(missing_ok=True)


def kor(tyst=False, rendera_ocksa=True):
    """(antal kontroller, fel). prov.py anropar den har, sa mappningen provas
    av provsviten och inte bara nar nagon rakar kora skriptet. Ett orakel som
    inte kors av prov.py ar ett orakel som inte finns."""
    global fel, kontroller
    fel, kontroller = [], 0
    for m in MALLAR:
        mat(m, skriv=not tyst)
    if rendera_ocksa:
        tomma_sektioner(tyst=tyst)
    return kontroller, list(fel)


def las(mall):
    return (json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8")),
            (HAR / "fall" / (mall + ".html")).read_text(encoding="utf-8"))


def sjalvprov():
    """ATT PROVET KAN FALLA. Varje kontroll ovan mutaras i MINNET - aldrig
    pa disk, sa ett avbrutet sjalvprov inte lamnar repot muterat - och
    maste bli rod. En kontroll som inte kan bli rod ar ingen kontroll."""
    global fel, kontroller

    def drop_kostnad(d, h):
        d["kostnader"] = d["kostnader"][1:]
        return d, h

    def kasta_om_kostnader(d, h):
        d["kostnader"][0], d["kostnader"][1] = d["kostnader"][1], d["kostnader"][0]
        return d, h

    def drop_forberedelse(d, h):
        d["forberedelser"] = d["forberedelser"][:-1]
        return d, h

    def andra_forberedelse(d, h):
        d["forberedelser"][0] = d["forberedelser"][0] + " Och en mening ingen bett om."
        return d, h

    def kasta_om_rader(d, h):
        r = d["order"]["rader"]
        r[0], r[-1] = r[-1], r[0]
        return d, h

    def drop_rad(d, h):
        d["order"]["rader"] = d["order"]["rader"][1:]
        return d, h

    def annan_villkorsurl(d, h):
        d["offert"]["villkor_url"] = "https://ampy.se/nagot-annat"
        return d, h

    def tomt_href(d, h):
        return d, h.replace('href="https://ampy.se/kopvillkor"', 'href=""')

    def synlig_tom_fold(d, h):
        d.pop("kostnader", None)
        return d, h

    def lanktexten_byts(d, h):
        return d, h.replace("Läs våra köpvillkor", "Läs villkoren")

    PROV = [
        ("en kostnadspost tas bort ur kontraktet", "laddbox", drop_kostnad),
        ("tva kostnadsposter byter plats", "laddbox", kasta_om_kostnader),
        ("en forberedelsepunkt tas bort", "batteri", drop_forberedelse),
        ("en forberedelsepunkts lydelse andras", "service", andra_forberedelse),
        ("forsta och sista ordraden byter plats", "tillagg", kasta_om_rader),
        ("en ordrad tas bort ur kontraktet", "elcentral", drop_rad),
        ("villkor_url pekar nagon annanstans an sidan", "batteri", annan_villkorsurl),
        ("villkorsfolden far ett TOMT href", "service", tomt_href),
        ("faltet saknas men folden star kvar SYNLIG", "laddbox", synlig_tom_fold),
        ("kopvillkorslankens lydelse byts", "elcentral", lanktexten_byts),
    ]
    slapp = 0
    for namn, mall, f in PROV:
        d, h = las(mall)
        d, h = f(d, h)
        fel, kontroller = [], 0
        mat(mall, d=d, html=h, skriv=False)
        if fel:
            print("  ROTT  %-44s %s" % (namn, fel[0][:96]))
        else:
            print("  GRONT %-44s SLAPPTE FORBI" % namn)
            slapp += 1
    print()
    print("%d mutationer, %d slapp forbi" % (len(PROV), slapp))
    return slapp


if __name__ == "__main__":
    if "--sjalvprov" in sys.argv:
        raise SystemExit(1 if sjalvprov() else 0)
    print("KONTRAKT -> SIDA, antal poster")
    for m in MALLAR:
        mat(m)
    print()
    print("UTAN FALTET: sektionen ska vara DOLD, matt pa en ny rendering")
    tomma_sektioner()
    print()
    print("%d kontroller" % kontroller)
    if fel:
        print("\n%d FEL:" % len(fel))
        for f in fel:
            print("  * " + f)
        raise SystemExit(1)
    print("alla gröna")
