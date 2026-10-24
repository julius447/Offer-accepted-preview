#!/usr/bin/env python3
"""Jämför det här repots kort med acceptskärmen i offertrepot.

    python3 verktyg/jamfor-skarm.py ~/Desktop/"Claude Code"/laddboxoffert

Samma skärm bor i två repon: index.html här och gemensamt/block/skarm-accept.html
där. De har ingen delad källa, så varje ändring måste göras två gånger eller så
glider de isär. Tills en delad källa finns är det här mätningen av glidningen.

LÄSER BARA. Skriver ingenting i det andra repot.
"""
import difflib
import pathlib
import re
import sys

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
HAR = pathlib.Path(__file__).resolve().parent.parent
annan = pathlib.Path(sys.argv[1]).expanduser() / "gemensamt" / "block" / "skarm-accept.html"
if not annan.exists():
    raise SystemExit("hittar inte " + str(annan))


def kort(html):
    """Bara <main class="oa__card">, normaliserad: ingen indentering, inga
    kommentarer, inga aurora-svg. Det är markupen som ska vara densamma."""
    m = re.search(r'<main class="oa__card">.*?</main>', html, re.S)
    if not m:
        raise SystemExit("hittar inget oa__card")
    s = re.sub(r"<!--.*?-->", "", m.group(0), flags=re.S)
    s = re.sub(r">\s+<", ">\n<", s)
    return [l.strip() for l in s.split("\n") if l.strip()]


a = kort((HAR / "index.html").read_text(encoding="utf-8"))
b = kort(annan.read_text(encoding="utf-8"))

# De skillnader som är AVSIKTLIGA och varför. Står en rad här är glidningen
# ett beslut, inte ett slarv. Allt annat är glidning som någon ska stänga.
AVSIKT = [
    # Varje post: (markörer på BÅDA sidor av diffen, skälet). Tas en rad bort
    # och en annan in för samma beslut måste båda formerna stå här, annars
    # rapporteras borttagningen som oförklarad.
    (('id="oaRef"', 'class="oa__ref">Offert'),
     'Referensbrickan: "#" ligger i markupen här och inne i spannet där. Varje datafil i '
     'offertrepot lagrar numret BART ("referens": "2026-0642", EL_OFFERTNR = "2026-0641"), '
     'så en data-oa-fyllning med ett bart värde skriver "Offert 2026-0640" och tappar '
     'brickans tecken. Etiketten varierar dessutom: en tilläggsoffert säger '
     '"Tillägg till offert" och pekar på modern.'),
    (('oa__kvitto-not', 'id="oaPaket"'),
     'Kvittonoten fylls ur kontraktet här och står som fast text där. Texten måste följa '
     'vilka potter ordern faktiskt har: en bekräftelse VET potterna, acceptskärmen inne i '
     'offerten gör det inte. Dessutom står där id="oaPaket" med ordet "Paket" som fast '
     'innehåll, och det ordet syns om skriptet inte hinner fylla rutan. Här är spannet '
     'tomt. ORDEN jämförs separat nedan, för en förklaring som bara säger "mekanismen '
     'skiljer" döljer att LYDELSEN drar isär. Den här raden gjorde precis det: den '
     'citerade "inkl. moms, efter avdrag" i fem dagar efter att offertrepot bytt till '
     '"inkl. moms, efter skattereduktion".'),
    (('data-oa-steg', 'class="oa__step-text">', 'data-oa="bokare.namn"'),
     'Stegen har datakrokar här, så en mall kan byta eller ta bort ett steg utan att forka '
     'sidan. Tilläggsmallen gör redan bytet med strängersättningar och en regex i '
     'offerter/tillagg/offert.py rad 230 till 240.'),
    (('Vi ringer och bokar tid',),
     'Standardmeningen bär inget namn här. Där står "Rasmus" och i den publika spegeln '
     '"[Bokare]". En platshållare i hakparenteser får aldrig nå en kund: saknas namnet '
     'skrivs meningen utan det.'),
    (('oa__order', 'Det här accepterade du', '</section>'),
     'Ordersektionen finns bara här. Acceptskärmen inne i offerten har hela offerten en '
     'skärm upp; den fristående bekräftelsen har inget annat.'),
    (('id="oaTitel"', 'class="oa__title">'),
     'Rubriken har en datakrok här. Tilläggsmallen byter redan ut den till '
     '"Ditt tillägg är nu accepterat!".'),
    (('oaProd',), 'Produktraden finns bara här, av samma skäl som ordersektionen.'),
    (('oaIngar',), 'Punktlistan "Allt som ingår" finns bara här. Serviceofferten har ingen '
                   'produktbild och inga val: listan ÄR ordern.'),
    (('oaRader',), 'Radlistan finns bara här.'),
    (('oaNot',), 'Noten under raderna finns bara här.'),
    (('oaFin',), 'Finstilten och köpvillkorslänken finns bara här.'),
    (('id="oaSteps"', '<ol class="oa__steps">'),
     'Steglistan har id här, så ett borttaget steg kan hittas utan att gissa.'),
]

diff = [l for l in difflib.unified_diff(b, a, "offertrepot", "det här repot", lineterm="", n=0)
        if l[:1] in "+-" and l[:3] not in ("+++", "---")]

oforklarat = []
for rad in diff:
    if not any(any(n in rad for n in nycklar) for nycklar, _ in AVSIKT):
        oforklarat.append(rad)

print("Jämför  %s\n   mot  %s\n" % ((HAR / "index.html").as_posix(), annan))
print("%d rader skiljer." % len(diff))
sedda = set()
for nycklar, skal in AVSIKT:
    if any(any(n in r for n in nycklar) for r in diff) and nycklar[0] not in sedda:
        sedda.add(nycklar[0])
        print("\n  AVSIKT  %s\n          %s" % (nycklar[0], skal))
if oforklarat:
    print("\n%d OFÖRKLARAD GLIDNING:" % len(oforklarat))
    for r in oforklarat:
        print("  " + r[:160])
    sys.exit(1)
# ----------------------------------------------------------------- ORDEN
# Markupen kan vara förklarad medan LYDELSEN glider. Kvittonoten är fast text
# i offertrepot och räknas här, och de två måste säga samma sak om moms och
# avdrag. Ägarens lydelse D3 24 oktober: "inkl. moms, efter skattereduktion
# (Grön teknik och ROT)." Offertrepots delade skärm bär första ledet utan
# parentesen, för den vet inte vilka potter ordern har. Bekräftelsen vet, och
# fyller parentesen. Regeln: bekräftelsens korta sats BÖRJAR med offertrepots.
import json

annan_text = annan.read_text(encoding="utf-8")
m = re.search(r'class="oa__kvitto-not"[^>]*>([^<]+)<', annan_text)
if not m:
    print("\nORDEN: hittar ingen oa__kvitto-not i offertrepot, kan inte jämföra lydelsen")
    sys.exit(1)
deras = m.group(1).strip()

js = (HAR / "script.js").read_text(encoding="utf-8")
mina = re.findall(r"forsta = '([^']*)'", js)
if not mina:
    print("\nORDEN: hittar ingen pottrad i script.js")
    sys.exit(1)

print("\nORDEN")
print("  offertrepots fasta text : %r" % deras)
fel_ord = []
# BARA ÅT ETT HÅLL. Ett dubbelriktat prefixprov godkänner också en KORTARE
# sats, och "inkl. moms, efter " är ett prefix av offertrepots text fast den
# har tappat ordet skattereduktion. Uppmätt: med `or deras.startswith(f)` gav
# provet grönt på precis den regressionen. Undantaget är "inkl. moms" utan
# pott, som inte kan bära ordet skattereduktion eftersom ingen dras.
for f in mina:
    passar = f == "inkl. moms" or f.startswith(deras)
    print("  bekräftelsens sats      : %-56r %s" % (f, "ok" if passar else "GLIDNING"))
    if not passar:
        fel_ord.append(f)
if fel_ord:
    print("\n%d lydelser säger något annat om moms och avdrag än offertrepot." % len(fel_ord))
    sys.exit(1)

print("\nIngen oförklarad glidning, och lydelserna säger samma sak.")
