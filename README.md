# Orderbekräftelsen

Den sida kunden får när hon accepterat en offert. **En sida för fem offertmallar**: laddbox,
elcentral, batterilagring, service och tilläggsoffert.

Designen är ägargodkänd och görs inte om. Det som är byggt här är **logiken**: sidan renderar
ur ett kontrakt, `AMPY_ORDER`, och varje tillägg i layouten ligger i samma formspråk som de
tre sektioner som redan fanns.

* **[`KONTRAKT.md`](KONTRAKT.md)** är dokumentet. Fält för fält, vilken mall som fyller vad,
  och vad som händer när ett fält saknas.
* `index.html` är produktionssidan. Utan kontrakt visar den **inte ett enda tal**: inga
  exempelvärden, ingen platshållare, inget hårdkodat offertnummer eller datum.
* `exempel/*.json` är fem kontrakt, ett per mall. Varje tal i dem är hämtat ur offertrepot,
  med källan skriven i filens eget `_kallor`.
* `fall/*.html` är de fem fallen renderade och sparade som **statisk markup**. Ingen
  JavaScript, inget kontrakt kvar i sidan: det är vad serversidan ska skicka.

## Köra

```bash
python3 bygg.py                 # bygger om fall/ ur index.html + exempel/
python3 prov.py                 # oraklet: 310 kontroller
python3 verktyg/matt.py fall/laddbox.html 375        # sidledes scroll, träffytor
python3 verktyg/typ.py fall/laddbox.html 390         # husets sju typstorlekar
python3 verktyg/skala.py                             # varje längd ur husets skalor
python3 verktyg/kontrast.py fall/laddbox.html        # WCAG AA
python3 verktyg/skarmbild.py fall/laddbox.html 375 ut.png 1660
python3 verktyg/ordagrant.py ~/Desktop/"Claude Code"/laddboxoffert     # varje kundsträng mot offertrepot
python3 verktyg/jamfor-skarm.py ~/Desktop/"Claude Code"/laddboxoffert  # glidning mot offertrepot
```

`bygg.py` kör `script.js` i headless Chrome och sparar DOM:en. **En renderare, inte två**: en
andra implementation i Python hade varit en andra sanning som kan glida.

Chrome körs alltid med egen `--user-data-dir` och dödas med sin egen process-grupp. Döda
aldrig Chrome med `pkill`: det stänger användarens riktiga webbläsare med alla flikar.

## De fyra invarianterna hantverket vilar på

De kom ur passet 24 oktober och de är alla kontroller i `prov.py`, inte råd. Varje
invariant är bevisad genom att defekten återinfördes och oraklet stoppade bygget.

1. **Ett belopp bryts aldrig mitt itu.** Hårdspatie både som tusentalsavgränsare och före
   "kr" (ägarbeslut A8, 24 okt). Uppmätt före: 25 av 25 belopp på de fem sidorna bar
   vanligt mellanslag före kr.
2. **Sju typstorlekar, inte fler:** 30 / 24 / 20 / 17 / 15 / 13 / 11, och **sex vikter**,
   300 till 800. Mäts i webbläsaren vid två bredder, inte läses ur CSS. Uppmätt före:
   elva storlekar vid 390 px, och en vikt 900 som ingen skrivit (webbläsarens `bolder`
   räknar upp från stycket) och som typsnittsfilen klamrade tyst.
3. **Varje längd ur husets skalor.** Spacing 2/4/8/12/16/24/32/48/64, storlekar
   16/20/24/32/44/48, radier 10/14/20/28. Undantagen är namngivna i `verktyg/skala.py`.
   Uppmätt före: 51 deklarationer utanför skalan, 28 distinkta värden.
4. **Varje sträng kunden ser är offertens egen, ordagrant, ur MALLENS egna filer.**
   `verktyg/ordagrant.py` läser offertrepot. Ett orakel som bara läser sitt eget repo kan
   inte upptäcka att sanningskällan rört sig, och tre fel överlevde till 24 oktober av
   precis det skälet. Att en sträng finns någonstans räcker inte: "Driftsättning och
   avprovning" är en helt riktig rad, i elcentralmallen, och gav grönt på servicemallens
   bekräftelse i ett dygn.

## Typsnittet

**Inter, självhostad.** Ägarbeslut 20 oktober, ordagrant ur offertrepots `bygg.py`:
*"Inter for ALLA offertmallar. Storst x-hojd av de fyra kandidaterna, och det ar hela
skillnaden vid 13 och 15 px."* Vikterna där är 300 till 800.

Sidan stod i Outfit till 24 oktober, alltså i husets typsnitt från före 16 oktober, och
`styles.css` påstod att filerna var samma produktionssubset som offertsidan använder. Det
var inte sant: samma kort renderades i två typsnitt i två repon.

**Självhostningen är med flit och behålls.** Offertmallarna hämtar Inter från
`fonts.googleapis.com`, vilket skickar kundens IP-adress till Google på en sida som bär
hennes namn och hennes pris. Den här sidan gör det inte.

## Det tre reglerna sidan inte böjer

1. **Alla belopp är netto**, efter avdrag och inklusive moms. Kontraktet har inget fält för en
   avdragsbas, en sats eller ett avdragsbelopp.
2. **ROT-avdragets belopp står aldrig på en sida.** Skyddet ligger i datat: det finns inget
   fält att hämta det ur, och `prov.py` stoppar varje sida som visar ett belopp som inte står
   i kontraktet.
3. **Ingenting skickas härifrån.** Ingen `fetch`, ingen lagring, inga URL-parametrar. Sidan är
   en läsare. Att accepten faktiskt når CRM:et är serverns jobb och finns **inte byggt** i
   någon mall i dag: det är det enda som står mellan kontraktet och en fungerande
   orderbekräftelse.

## Samma skärm bor i två repon

`index.html` här och `gemensamt/block/skarm-accept.html` i offertrepot är samma kort utan
delad källa. `verktyg/jamfor-skarm.py` mäter glidningen och namnger vilka skillnader som är
avsiktliga och varför. Tills en delad källa finns måste varje ändring göras två gånger.
