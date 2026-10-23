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
python3 prov.py                 # oraklet: 226 kontroller
python3 verktyg/matt.py fall/laddbox.html 375        # sidledes scroll, träffytor
python3 verktyg/kontrast.py fall/laddbox.html        # WCAG AA
python3 verktyg/skarmbild.py fall/laddbox.html 375 ut.png 1660
python3 verktyg/jamfor-skarm.py ~/Desktop/"Claude Code"/laddboxoffert   # glidning mot offertrepot
```

`bygg.py` kör `script.js` i headless Chrome och sparar DOM:en. **En renderare, inte två**: en
andra implementation i Python hade varit en andra sanning som kan glida.

Chrome körs alltid med egen `--user-data-dir` och dödas med sin egen process-grupp. Döda
aldrig Chrome med `pkill`: det stänger användarens riktiga webbläsare med alla flikar.

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
