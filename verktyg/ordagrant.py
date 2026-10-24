#!/usr/bin/env python3
"""Varje sträng kunden ser på bekräftelsen, sökt ORDAGRANT i offertrepot.

    python3 verktyg/ordagrant.py ~/Desktop/"Claude Code"/laddboxoffert

LÄSER BARA. Skriver ingenting i det andra repot.

VARFÖR DEN FINNS. Bekräftelsen skriver inte en enda egen mening om ordern:
varje rad, namn, spec och not är den sträng OFFERTEN gav, ordagrant. Men
offerten ändras, och då ändras inte bekräftelsen. Tre exempel, alla uppmätta
2026-10-24:

  * `exempel/batteri.json` bar specen "Delar av huset får ström från batteriet
    när nätet går ner" och påstod i sitt eget `_kallor` att den var ordagrant
    filens egen. Den meningen fanns inte i en enda fil i offertrepot: filen
    säger "Ström från batteriet när nätet går ner".
  * `exempel/service.json` bar TRE grundrader med "Driftsättning och
    avprovning" som en rad. Ägaren bytte listan 24 oktober (E4) och den har
    FYRA rader med "Driftsättning" och "Avprovning" var för sig.
  * Noten i `_kallor` pekade på generatorns orakel rad 232 till 236 som skäl.
    Det oraklet är pensionerat av precis det skälet: det bevakade listan från
    23 oktober. "Ett prov som bevakar en gammal sanning stoppar inte felet,
    det stoppar rättningen" (FALLOR.md).

INGEN AV DE TRE SYNTES I prov.py, för prov.py läser bara det här repot. Ett
orakel som aldrig tittar på sanningskällan kan inte upptäcka att den rört sig.

OM EN STRÄNG INTE HITTAS är det antingen glidning eller en sträng offerten
KOMPONERAR i körning (grannrabattens not byggs av kr() och ett antal; steg 2
på service av "Du har valt " + TID[tid] + "..."). Därför måste varje miss
förklaras i kontraktets `_undantag_ordagrant`, med skäl. En oförklarad miss
är ett fel. En förklaring som inte längre stämmer syns genom att strängen
plötsligt hittas och undantaget blir onödigt, och det rapporteras också.
"""
import json
import pathlib
import sys

HAR = pathlib.Path(__file__).resolve().parent.parent
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]

# Fälten som når kundens öga. `etikett` står inte här: "Att betala" är sidans
# egen etikett bredvid totalen, inte en sträng ur en mall.
FALT = {"titel", "rubrik", "underrubrik", "namn", "spec", "variant",
        "i_stallet_for", "notis", "text", "ord", "not", "under"}

BINARA = {".png", ".jpg", ".jpeg", ".webp", ".woff2", ".woff", ".ttf",
          ".pdf", ".ico", ".zip", ".gz", ".mp4"}

# VARJE MALL SOKER I SINA EGNA FILER.
#
# Att en strang finns NAGONSTANS i offertrepot ar inte samma sak som att den
# ar rätt. Uppmatt 2026-10-24: servicebekraftelsen bar "Driftsattning och
# avprovning" som EN rad. Agaren bytte listan 24 oktober (E4) till fyra rader
# med "Driftsattning" och "Avprovning" var for sig. Den gamla strangen gav
# anda gront, for den finns kvar och ar helt riktig: i ELCENTRALMALLEN, som
# har en egen lista dar den raden hor hemma. Ett prov som bara fragar "finns
# den?" godkanner alltsa att en mall lanar en annan malls copy.
#
# Darfor soks varje malls strangar i mallens EGNA filer, plus det tre mallar
# faktiskt delar: katalogen, gemensamt/ och mallens byggda sida.
SOKVAGAR = {
    "laddbox":   ["offerter/laddbox/", "katalog/", "gemensamt/", "offert-zaptec-go.html"],
    "elcentral": ["offerter/elcentral/", "katalog/", "gemensamt/", "elcentral.html"],
    "batteri":   ["offerter/batteri/", "katalog/", "gemensamt/", "offert-batteri-saj-hs3.html"],
    "service":   ["offerter/service/", "katalog/", "gemensamt/", "service.html"],
    "tillagg":   ["offerter/tillagg/", "katalog/", "gemensamt/", "tillagg.html"],
}


def las_nordstjarnan(rot):
    filer = []
    for p in rot.rglob("*"):
        if p.is_dir():
            continue
        if ".git" in p.parts or "__pycache__" in p.parts or "node_modules" in p.parts:
            continue
        if p.suffix.lower() in BINARA:
            continue
        try:
            filer.append((p.relative_to(rot).as_posix(), p.read_text(encoding="utf-8")))
        except Exception:
            pass
    return filer


def strangar(o, vag=""):
    if isinstance(o, dict):
        for k, v in o.items():
            if k.startswith("_"):
                continue
            if k in FALT and isinstance(v, str) and v.strip():
                yield (vag + "." + k, v.strip())
            yield from strangar(v, vag + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strangar(v, vag + "[%d]" % i)


def kor(rot, tyst=False):
    """(antal kontrollerade, [fel]) mot offertrepot i `rot`."""
    filer = las_nordstjarnan(rot)
    if len(filer) < 50:
        return 0, ["%s ser inte ut som offertrepot: bara %d lasbara filer" % (rot, len(filer))]
    antal, fel = 0, []
    for mall in MALLAR:
        d = json.loads((HAR / "exempel" / (mall + ".json")).read_text(encoding="utf-8"))
        undantag = d.get("_undantag_ordagrant") or {}
        anvanda = set()
        omrade = SOKVAGAR[mall]
        mina = [(n, t) for n, t in filer
                if any(n == v or n.startswith(v) for v in omrade)]
        if len(mina) < 5:
            fel.append("%s: hittar bara %d filer under %s" % (mall, len(mina), omrade))
        for vag, s in strangar(d):
            antal += 1
            traff = next((n for n, t in mina if s in t), None)
            if traff:
                if vag in undantag:
                    fel.append("%s: %s star ORDAGRANT i %s men har ett undantag. "
                               "Ta bort undantaget." % (mall, vag, traff))
                    anvanda.add(vag)
                continue
            if vag in undantag:
                anvanda.add(vag)
                if not tyst:
                    print("   undantag %-9s %-28s %s" % (mall, vag, undantag[vag][:70]))
                continue
            # Finns den i en ANNAN malls filer ar det en lanad rad, och det
            # ar ett annat och varre fel an en strang som inte finns alls.
            annan = next((n for n, t in filer if s in t), None)
            if annan:
                fel.append("%s: %s star inte i mallens egna filer, men i %s. "
                           "En mall far inte bara en annan malls copy: %r"
                           % (mall, vag, annan, s[:70]))
            else:
                fel.append("%s: %s star inte ordagrant i offertrepot: %r" % (mall, vag, s[:80]))
        for vag in undantag:
            if vag not in anvanda:
                fel.append("%s: _undantag_ordagrant har %s, men det finns ingen sadan strang"
                           % (mall, vag))
    return antal, fel


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    rot = pathlib.Path(sys.argv[1]).expanduser().resolve()
    if not rot.exists():
        raise SystemExit("hittar inte " + str(rot))
    print("Nordstjarnan: %s\n" % rot)
    antal, fel = kor(rot)
    print("\n%d strangar kontrollerade" % antal)
    for f in fel:
        print("  * " + f)
    sys.exit(1 if fel else 0)
