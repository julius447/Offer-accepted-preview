# AMPY_ORDER, kontraktet mellan offerten och orderbekräftelsen

Orderbekräftelsen är EN sida för FEM offertmallar. Allt den visar kommer ur ett objekt,
`AMPY_ORDER`. Sidan räknar ingenting, hittar inte på något, och visar inget den inte fått.

* **Fyll det ur CRM:et.** Sanningskällan är CRM:et, inte sidan. Sidan är en läsare.
* **Rendera värdena i markupen (SSR).** Då är `script.js` en no-op och sidan fungerar med
  JavaScript avstängt. En accepterad order är en handling kunden sparar och skriver ut.
  Alternativt skriver servern ut `window.AMPY_ORDER` i sidan och skriptet fyller. Filerna i
  `fall/` är byggda den andra vägen och sparade som den första, så de är samma sak.
* **Aldrig URL-parametrar.** Priser och radinnehåll i en query-sträng är manipulerbara och
  hamnar i loggar och referrers. Sidan sätter redan `referrer: no-referrer` och
  `robots: noindex, nofollow`.
* **Aldrig `localStorage`.** Kunden öppnar bekräftelsen i mejlet på en annan enhet än den
  där hon accepterade. Ordern bor på servern, hämtad med tokenet i länken.

---

## 0. De tre besluten kontraktet vilar på

**1. Alla belopp är NETTO: efter avdrag och inklusive moms.**
Ägarbesked 2026-10-22: "Elcentral och installation för 5 990 är inklusive moms efter
ROT-avdrag." Katalogens priser är netto (`katalog/tillval.json` rad 2 och 4), batteriets
prislista är kundens pris efter grön teknik, och elcentralmotorn slutade dra avdrag
2026-10-23. Kontraktet har därför **inget fält för en avdragsbas, en sats eller ett
avdragsbelopp**, och sidan räknar inget avdrag.

**2. ROT-avdragets belopp får aldrig stå på en sida.**
Ägardirektiv 2026-10-23, i versaler: "VI KOMMER ALDRIG SKRIVA UT HUR MYCKET ROT AVDRAGET PÅ
ELCENTRAL UPPGÅR TILL. VI VISAR BARA TOTALSUMMAN SOM ÄR PRISET EFTER ROT INKL MOMS."
Skyddet ligger i datat, inte i copyn: det finns inget fält att hämta ett avdragsbelopp ur.
`prov.py` stoppar dessutom varje kontrakt som bär ett fält som heter något i stil med
`sats`, `fore_avdrag`, `arbetsandel` eller `rot_belopp`, och varje byggd sida som visar ett
belopp som inte står i kontraktet.
Grön teknik-halveringen i laddboxens hjälte är godkänd sedan tidigare och är en annan sak:
den står i OFFERTEN, inte här.

**3. Ingenting skickas härifrån.**
Det finns ingen `fetch`, `XMLHttpRequest`, `sendBeacon` eller `form action` i någon mall, och
inte heller här. Sidan säger att accepten är registrerad, och det löftet hålls av servern som
renderar den. Det är ett erkänt gap i offertrepots META. **Skriv inga nya löften om
leverans i de här fälten.** `prov.py` stoppar bygget om ett nytt dyker upp.

---

## 1. Hela kontraktet

```json
{
  "kontrakt_version": 1,
  "priser_ar": "netto",

  "offert": {
    "referens":         "2026-0640",
    "mall":             "laddbox",
    "titel":            null,
    "ar_tillagg":       false,
    "moderreferens":    null,
    "modertyp":         null,
    "giltig_till_lang": null,
    "accepterad":       "2026-10-25",
    "villkor_url":      "https://ampy.se/kopvillkor"
  },

  "bokare": { "fornamn": "Rasmus" },

  "steg": [],

  "order": {
    "rubrik":      "Zaptec Go",
    "underrubrik": "22 kW med Perific Max",
    "etikett":     "Att betala",
    "total":       14345,
    "paket":       { "namn": "Paket Premium", "spec": null, "belopp": 9170, "avdrag": "gron-teknik" },
    "rader":       [ ... ],
    "ingar":       [ ... ],
    "utestaende":  [ ... ]
  }
}
```

---

## 2. Fält för fält

### Toppnivå

| Fält | Typ | Krävs | Saknas, då | Fylls av |
|---|---|---|---|---|
| `kontrakt_version` | heltal | ja | ingen rendering garanteras | CRM. Fem mallar som fyller samma objekt över tid måste kunna versionsstyras utan att gamla sparade bekräftelser slutar rendera. |
| `priser_ar` | `"netto"` | ja | **inget belopp renderas alls**, inget kvitto, ingen prisrad | CRM. Fältet har **ingen default** med flit: det är exakt den tvetydigheten som gjorde att samma lilla elcentral kostade 5 990 kr på laddboxsidan och 4 552 kr på elcentralsidan. |
| `offert` | objekt | ja | tomt objekt tolkas som allt saknas | CRM |
| `bokare` | objekt | nej | steg 2 skrivs utan namn: "Vi ringer och bokar tid" | CRM |
| `steg` | lista | nej | markupens godkända copy står kvar | mallen |
| `order` | objekt | nej | ordersektionen visas inte alls | CRM |

### `offert`

| Fält | Typ | Saknas, då | Fylls av |
|---|---|---|---|
| `referens` | sträng, **bart nummer utan `#`** | referensbrickan visas inte | CRM. Markupen äger `#`. Varje datafil i offertrepot lagrar numret bart (`"referens": "2026-0642"`, `EL_OFFERTNR = "2026-0641"`), så ett värde med `#` ger `##`. |
| `mall` | `laddbox` \| `elcentral` \| `batteri` \| `service` \| `tillagg` | ingen effekt på renderingen; fältet är för spårbarhet | mallen. **`[GAP]`** Den femte heter "tilläggsoffert" i uppdraget och "elektriker" i `offerter/LAS-MIG.md` rad 3. |
| `titel` | sträng | rubriken "Din offert är nu accepterad!" står kvar | mallen. Tilläggsmallen sätter "Ditt tillägg är nu accepterat!" ordagrant som i `offerter/tillagg/offert.py` rad 228. Sätts den ändras också flikrubriken och utskriftens sidhuvud. |
| `ar_tillagg` | bool | `false` | mallen. `true` byter brickans etikett till "Tillägg till offert" och visar `moderreferens` i stället för `referens`. |
| `moderreferens` | sträng | **`ar_tillagg: true` utan den stänger totalen** | mallen. Utan den ser kunden två orelaterade nummer. |
| `modertyp` | sträng | ingen effekt i dag | mallen, för spårbarhet. `MODERTYP` i `offerter/tillagg/offert.py` rad 64. |
| `giltig_till_lang` | sträng, t.ex. "27 oktober 2026" | meningen renderas **utan datum**. Aldrig en platshållare, aldrig ett gissat datum. | CRM. Används av avböjsskärmens tvilling (`skarm-avboj.html` rad 40). Den accepterade sidan skriver inget datum i dag: offerten är accepterad, och ett giltighetsdatum där är en ägargrind. Fältet finns så att **ingen hårdkodar det**, vilket är precis vad som hänt i dag ("27 oktober 2026" står som bokstavlig sträng i markupen och byts med `str.replace` i `offerter/elcentral/offert.py` rad 697). |
| `accepterad` | sträng, ISO 8601, t.ex. `"2026-10-25"` | **ingen mening skrivs**. Aldrig en platshållare, aldrig ett gissat datum, och ordet "Accepterad" står inte där ensamt. | CRM, i det ögonblick kunden trycker acceptera. **ÄGARSVAR 46, 25 oktober: "Ja, lägg till datum."** Sidan skriver den svenska formen ("25 oktober 2026") ur ISO-datumet, så de fem mallarna inte kan visa fem former; `prov.py` skriver samma form själv i stället för att läsa sidans. Ett datum som inte finns i kalendern (2026-02-30) **stänger totalen**: ett kontrakt som har fel om datumet är ett kontrakt som har fel, och sidan väljer inte vilka fel den bryr sig om. **Ett acceptdatum drar inte med sig ett `giltig till`:** offerten har ingen giltighetstid (ägardirektiv 23 okt), och `prov.py` stoppar varje sida som skriver ett. |
| `villkor_url` | URL | **ingen länk renderas, aldrig ett tomt `href`** | CRM. `https://ampy.se/kopvillkor`, kontrollerad 19 okt, samma adress alla fem mallarna länkar till. Länktexten är deras, ordagrant: "Läs våra köpvillkor". På papper skrivs adressen ut efter länken, så villkoren når papperet. |

### `bokare`

| Fält | Typ | Saknas, då | Fylls av |
|---|---|---|---|
| `fornamn` | sträng | steg 2 blir "Vi ringer och bokar tid" | mallen. Laddbox: Rasmus. Elcentral: Felix (`offerter/elcentral/offert.py` rad 56). Batteri: Rasmus. Service: Rasmus (`offerter/service/jobb.json` rad 31). Tillägg: **ingen**, elektrikern är på plats, och tilläggsmallens orakel stoppar bygget om Rasmus eller Felix står på sidan. **`[GAP]`** Elektrikerns namn finns inte i repot. |

**Platshållare får aldrig nå en kund.** Den publika spegeln bär i dag `[Bokare]` i hakparenteser
på rad 46. Det är därför standardmeningen här är namnlös i stället för att vara en platshållare.

### `steg`

En lista med upp till tre poster som **skriver över** markupens godkända copy. En post är
`null` när steget står som det är.

| Fält | Typ | Betyder |
|---|---|---|
| `rubrik` | sträng | ersätter stegets rubrik |
| `under` | sträng eller `null` | ersätter underraden; `null` tar bort den |
| `ta_bort` | `true` | tar bort hela steget, och de som står kvar numreras om |

Varför fältet finns: "ringer och bokar tid" är **fel** på en tilläggsoffert där elektrikern
redan står hos kunden. Tilläggsmallen gör redan bytet med en strängersättning och en regex
(`offerter/tillagg/offert.py` rad 230 till 240). Med kontraktet behöver mall fyra och fem inte
forka sidan.

> **Mätt mot uppdraget.** Påståendet "copyn *ringer och bokar tid* är fel när kunden betalat
> för Express och tiden redan är överenskommen" **håller inte för Express**. Express är ett
> tidsFÖNSTER, 24 till 72 timmar (`offerter/service/jobb.json` rad 59, `TID` i
> `offerter/laddbox/skript.js` rad 10), inte en bokad tid. Samtalet ska alltså fortfarande
> komma. Servicemallen skriver själv "Du har valt Express, 24 till 72 timmar. Vi hör av oss
> för att boka tid." (`offerter/service/skript.js` rad 81), och det är den formuleringen
> `exempel/service.json` använder: fönstret kunden betalat för namnges, samtalet lovas kvar.
> Påståendet **håller för tilläggsofferten**, där elektrikern står i kundens hall, och där är
> steg 2 utbytt och steg 3 borttaget.

### `order`

| Fält | Typ | Saknas, då | Fylls av |
|---|---|---|---|
| `rubrik` | sträng | produktraden visas inte | mallen. Laddbox: modellnamnet (`prodName`). Elcentral: "Elcentral + installation", ägarbesked 19 okt. Batteri: modellnamnet. **Service och tillägg: `null`** (ingen produkt, ingen bild). |
| `underrubrik` | sträng | produktraden står utan underrad | mallen. Laddbox: paketets `spec`. Elcentral: storlekens `passar`-text. Batteri: "20 kWh, monterad och driftsatt". |
| `etikett` | sträng | "Att betala" | mallen. Etiketten bredvid totalen. **Får aldrig vara ett radnamn**: "Paket Premium 14 345 kr" i huvudet och "Paket Premium 9 170 kr" i raden under säger två saker om samma namn. "Att betala" är den etikett alla fem mallarna redan sätter bredvid sin total (`offerter/laddbox/body.html` rad 388, elcentral rad 210, batteri rad 114, service rad 72, tillagg rad 35). |
| `total` | heltal, netto | **inget totalbelopp renderas**, kvittot visas inte | CRM |
| `paket` | objekt eller **`null`** | ingen huvudrad; radlistan står ensam | mallen. **`null` är ett giltigt och vanligt värde**: service och tilläggsoffert har ingen paketlogik. |
| `rader` | lista, **aldrig `null`** | tom lista är i sin ordning | mallen |
| `ingar` | lista | ingen punktlista | mallen. Service fyller den; de andra lämnar den tom. |
| `utestaende` | lista | inga rader | mallen. Grannrabatten är enda fallet i dag. |

### `order.paket`

| Fält | Typ | Betyder |
|---|---|---|
| `namn` | sträng | radens etikett, **ordagrant**. Sidan komponerar ingen etikett åt fem mallar: laddboxen säger "Paket Premium", elcentralen "Liten", batteriet "SAJ HS3, 20 kWh". |
| `spec` | sträng eller `null` | underrad |
| `belopp` | heltal, netto | |
| `avdrag` | `gron-teknik` \| `rot` \| `inget` | |

### `order.rader[]`

| Fält | Typ | Betyder |
|---|---|---|
| `typ` | `tillagg` \| `huvud` \| `mellanskillnad` \| `intresseanmalan` | `huvud` är jobbet på en mall utan paket (service). `mellanskillnad` **kräver** `i_stallet_for`. `intresseanmalan` **kräver** `belopp: null` och summeras aldrig. |
| `namn` | sträng | |
| `variant` | sträng eller `null` | skrivs som "Namn, variant" |
| `spec` | sträng eller `null` | underrad |
| `antal` | heltal eller `null` | **eget fält, inte inbakat i namnet.** `radNamn()` i `offerter/laddbox/skript.js` rad 44 till 53 bakar in "6 stycken" i strängen; elcentralen håller det som eget fält. Utan `antal` och `styckpris` separat kan bekräftelsen inte visa "6 stycken, 800 kr per styck". |
| `styckpris` | heltal eller `null` | |
| `i_stallet_for` | sträng | **krävs på `mellanskillnad`.** En kabel som ingår i paketet är betald i 5-metersutförande; väljer kunden 10 meter betalar hon skillnaden. En lista som skriver namn och belopp rakt upp säger att en laddkabel kostar 200 kr. |
| `belopp` | heltal eller `null` | netto |
| `avdrag` | `gron-teknik` \| `rot` \| `inget` | **krävs på varje rad** |
| `notis` | sträng | ersätter beloppet när det är `null`. Standard: "ingen kostnad nu". |

### `order.ingar[]`

En sträng, eller `{ "text": "...", "spec": "..." }`. Renderas med samma bock som varje
punktlista i offerten (`gemensamt/bitar.py` rad 10). Serviceofferten är den enda mall som inte
konfigurerar något: kunden läser en lista och svarar ja eller nej, och då **är** listan ordern.

### `order.utestaende[]`

Ett löfte offerten gav och som bekräftelsen ska kvittera.

| Fält | Typ | Betyder |
|---|---|---|
| `text` | sträng | radens etikett, t.ex. "Grannrabatt, 3 grannar inbjudna" |
| `ord` | sträng | står där beloppet annars stått, t.ex. "dras när de beställt" |
| `not` | sträng | noten under listan |

**Texten skrivs av den mall som gav löftet, ordagrant.** Sidan komponerar ingenting här.
Grannrabattens tre strängar står i `offerter/laddbox/skript.js` rad 358 till 360.

---

## 3. Avdragsvokabuläret: tre värden, inte fyra stavningar

`gron-teknik` | `rot` | `inget`. Det är de tre värden `katalog/tillval.json` redan använder
(rad 28, 213, 296) och den fil `gemensamt/orakel.py` redan läser.

| Lager i dag | Fält | Värden | Mappas till |
|---|---|---|---|
| Laddboxkatalogen | `avdrag` | `gron-teknik`, `rot`, `inget` | oförändrat |
| Elcentralkatalogen | `avdrag` | `gt`, `rot`, `null` | `gt` → `gron-teknik`, `null` → `inget` |
| Laddboxmarkupen | `data-rot` | `"1"` eller attributet saknas | `"1"` → `rot`, saknas → `gron-teknik` |
| Elcentralmarkupen | `data-avdrag` | `rot`, `gt`, tom sträng | `gt` → `gron-teknik`, tom → `inget` |

**Mappningen görs av den som fyller kontraktet, inte av sidan.** Tar sidan emot fyra
stavningar lever fyra stavningar vidare. Ett okänt värde **stänger totalen**: utan att veta
vilken pott en prisrad hör till går finstilten om moms och avdrag inte att skriva sant, och
finstilten är det juridiska påståendet.

Lägg **aldrig** en rad i två potter. Det var felet som gav "minus 17 390 kr" på laddboxsidan
(`katalog/tillval.json` rad 317).

---

## 4. Invarianter, och vad som händer när de bryts

Sidan **stänger**, den gissar inte. Ett tal som inte stämmer med raderna över det är värre än
inget tal, för kunden kan inte se vilket av dem som är fel.

| # | Invariant | Bryts den |
|---|---|---|
| 1 | `priser_ar === "netto"` | inget belopp renderas alls |
| 2 | `order.total` = `paket.belopp` + summan av `rader[].belopp` | inget totalbelopp, inget kvitto |
| 3 | `avdrag` är exakt ett av `gron-teknik`, `rot`, `inget`, på varje rad med ett belopp | inget totalbelopp |
| 4 | `typ: "intresseanmalan"` har `belopp: null` och summeras aldrig | beloppet nollas och felet flaggas |
| 5 | `typ: "mellanskillnad"` har `i_stallet_for` | inget totalbelopp |
| 6 | `ar_tillagg: true` har `moderreferens` | inget totalbelopp |
| 7 | Saknas en sträng renderas meningen utan den | aldrig en platshållare, aldrig ett gissat datum, aldrig ett tomt `href` |
| 8 | `paket` får vara `null`, `rader` får vara tom men aldrig `null` | |
| 9 | Potterna **härleds** ur raderna och står inte i kontraktet | ett fält som kan motsäga raderna kommer att motsäga raderna |
| 10 | Bara rader **med ett belopp** sätter en pott och bär en pottmärkning | en intresseanmälan dras inte, så "Utan avdrag" bredvid "ingen kostnad nu" är brus |
| 11 | Två potter: varje prisrad märks. En pott: ingen rad märks | samma regel som `offerter/tillagg/offert.py` rad 287 till 292 |
| 12 | `accepterad` är `null` eller ett datum som finns i kalendern | inget totalbelopp, och ingen mening om datum |
| 13 | **En accepterad offert, en bekräftelse, ett nummer.** Sidan visar exakt ETT offertnummer, och det är kontraktets eget. Radlistan är exakt kontraktets egna rader. | provet stoppar bygget |
| 14 | **Varje tal kunden ser är härlett ur offertrepots egna källfiler**, med källan per operand i `_tal` | provet stoppar bygget |

Felen hamnar i `data-oa-fel` på `.oa` och i konsolen. Kunden ser bara att ett tal uteblev.

Finstilten under raderna och den korta satsen i kvittot byggs av `pottrad()`, **ordagrant
porterad** ur `offerter/tillagg/offert.py:pottrad`. Funktionen, inte ett radnummer: raderna
flyttar sig och en hänvisning till rad 162 pekade på något annat inom ett dygn. En mening om
moms och avdrag får inte finnas i två versioner i två repon.

**Ägarens lydelse, D3 24 oktober, ordagrant:** *"inkl. moms, efter skattereduktion (Grön
teknik och ROT). Avdragen dras direkt på fakturan."* Parentesen bär de potter ordern
faktiskt har. Den delade acceptskärmen i offertrepot säger samma mening utan parentes, för
den vet inte vilka potter ordern har; `verktyg/jamfor-skarm.py` mäter att de två börjar
likadant. **Meningen "ROT förutsätter att du har avdragsutrymme kvar." står inte här, och kan inte
komma tillbaka.** ÄGARSVAR 48, 25 oktober, ordagrant: *"Ta bort den raden från alla
offerter samt orderbekräftelse. Detta står redan i våra köpvillkor och är inte vårt ansvar
utan kundens."* Ägargrinden som stod här är därmed **stängd**, och skyddet ligger inte i
den här meningen utan i ett orakel: `prov.py:inget_avdragsutrymme` läser markupen,
renderaren och varje kundsträng i de fem kontrakten, och stoppar bygget om ordet dyker upp.
De tre vägarna in är provade var för sig genom att meningen återinförts i var och en.

Att markupen räknas och inte den synliga texten är ett mätfel som rättats: första versionen
läste `synlig(index)`, och i `index.html` är varje fyllbart element dolt tills ett kontrakt
fyller det. Meningen inskriven i det dolda `oaFin` gav grönt prov.

---

## 4b. En accepterad offert, en bekräftelse

**ÄGARSVAR 56, 25 oktober, ordagrant:** *"Vi måste se det som två olika offerter. Om en kund
har accepterat en laddboxoffert kommer de att få en orderbekräftelse för den. Har elektrikern
sedan varit där, gjort en offert för tillägg och skickat den, får de en orderbekräftelse på
tilläggen. Det blir inte en ny orderbekräftelse på laddboxen. Alltså är det separat. För varje
offert som accepteras får man en unik orderbekräftelse."*

Fyra mått, inte fyra påståenden. De körs på de fem byggda sidorna vid varje prov:

1. **Exakt ett offertnummer per sida**, läst ur den synliga texten. Alla träffar, inte den
   första: offertrepots eget orakel läste `re.search`, och på servicemallen var första
   träffen laddboxens 2026-0640 ur den delade acceptskärmen. Mallens eget 2026-0643 stod
   längre ner och sågs aldrig.
2. **Numret är kontraktets eget.** Sidan och kontraktet jämförs, så en sida inte kan bära ett
   nummer dess egen order inte känner till.
3. **Två egna offerter delar aldrig nummer.** Uppmätt 25 okt: laddbox 2026-0640, elcentral
   0641, batteri 0642, service 0643, var och en på sin egen sida och ingen annanstans.
4. **Radlistan är exakt kontraktets egna rader**, i ordning. Det är provet som gör "det blir
   inte en ny orderbekräftelse på laddboxen" mätbart åt båda håll: en rad för lite är en order
   kunden inte ser, en för mycket är en annan offerts rad.

**Tilläggsofferten delar moderns nummer, med flit, och det provas.** Brickan säger "Tillägg
till offert #2026-0640", alltså att numret tillhör någon annan. Provet kräver att numret är
exakt den mall `modertyp` pekar ut, att den mallens egen bekräftelse bär samma nummer, och att
moderoffertens total, produktrubrik och paketnamn **inte** står någonstans på tilläggets sida.

**`[GAP]` kvar:** tillägget har inget eget offertnummer i repot (§6 punkt 3). Svar 56 säger att
varje accepterad offert får en unik bekräftelse, och tilläggets bekräftelse är unik som sida men
bär moderns nummer i brickan. Formen är en ägarfråga, och fältet `offert.referens` står tomt
och väntar.

---

## 4c. Talen går tillbaka till källan

**ÄGARSVAR 60, 25 oktober:** *"Bygg det nu."*

`prov.py` provade att sidans belopp står i **kontraktet** och att kontraktets belopp står på
**sidan**. Den kedjan kan vara hel medan kontraktet, som är en kopia av offertens sanning, har
driftat: provet sa bara att sidan är lika med sig själv, ett led längre bort.

`verktyg/talen.py` går till källfilen. Varje kontrakt bär ett `_tal`-block med en **härledning**
per tal och en **källa per operand**, och oraklet räknar om härledningen och slår upp varje
operand i offertrepots fil vid varje körning.

| Källform | Betyder |
|---|---|
| `fil#json.väg` | värdet på vägen MÅSTE vara talet. `[fält=värde]` väljer posten i en lista eller nyckeln i ett objekt, `$nyckel` sist ger nyckeln (ett paketpris som ÄR nyckeln i `paket.json`) |
| `fil@ankare` | talet ska stå som eget tal på en rad som bär ankaret. Ankaret krävs: ett löst tal i en lång fil bevisar ingenting |
| `.kontrakt.väg` | ett annat tal i samma kontrakt, som i sin tur måste ha en egen post |
| `val: <skäl>` | kundens eget val (hur många spotlights). Finns inte i någon fil och låtsas inte göra det |

Tre egenskaper gör skillnaden mot en handskriven lista:

* **Fälten räknas upp ur datat.** En ny rad i en offert får en ny väg automatiskt, och saknar
  den källa blir provet rött. En handskriven lista hade räknat upp precis de tal som redan var rätt.
* **Mallen får bara läsa sina egna filer**, samma regel som `ordagrant.py`: ett pris ur en annan
  malls fil är samma fel som en lånad copyrad.
* **Talen inne i de komponerade strängarna räknas också.** En sträng som hittas ordagrant i
  offertrepot bär sina siffror med sig; en sträng i `_undantag_ordagrant` finns inte i någon fil.
  Grannrabattens not sa "Upp till 1 500 kr av, 500 kr för varje granne" utan att något band
  1 500 till antalet inbjudna. Nu gör en post det: 1 500 = 500 gånger 3, där 500 kommer ur
  laddboxmotorn och 3 ur radens egen text.

**Oraklet visar att det kan falla.** `python3 verktyg/talen.py <offertrepot> --sjalvprov` kör sex
mutationer mot en kopia av båda sidorna (ingenting skrivs i offertrepot) och kräver att var och en
blir röd: ett ändrat belopp, en borttagen post, en text som säger fyra grannar när noten säger
1 500 kr, en ny rad utan källa, ett ändrat pris i offertrepots katalog, och en omskriven rad i
offertrepots laddboxmotor.

---

## 5. Vad varje mall fyller

| | laddbox | elcentral | batteri | service | tillägg |
|---|---|---|---|---|---|
| `offert.titel` | | | | | "Ditt tillägg är nu accepterat!" |
| `offert.referens` | 2026-0640 | 2026-0641 | 2026-0642 | 2026-0642 | `null` |
| `ar_tillagg` / `moderreferens` | | | | | `true` / 2026-0640 |
| `bokare.fornamn` | Rasmus | Felix | Rasmus | Rasmus | ingen |
| `steg` | | | | steg 2 namnger tidsfönstret | steg 2 bytt, steg 3 borttaget |
| `order.rubrik` | Zaptec Go | Elcentral + installation | SAJ HS3 | `null` | `null` |
| `order.paket` | Paket Premium | storleken | lagringsstorleken | `null` | `null` |
| `order.rader` | tillägg, mellanskillnad, intresseanmälan | tillägg | ö-drift | jobbet + tidsvalet | artiklarna |
| `order.ingar` | tom | tom | tom | **jobbet + grunden** | tom |
| `order.utestaende` | grannrabatt | tom | tom | tom | tom |
| potter | grön teknik + ROT | ROT | grön teknik | ROT | grön teknik + ROT |

---

## 6. `[GAP]`, ägaren avgör

1. **Femte mallens namn.** "tilläggsoffert" i uppdraget, "elektriker" i `offerter/LAS-MIG.md` rad 3.
2. ~~**Offertnumret 2026-0642 används av två mallar.**~~ **STÄNGT.** Serviceofferten flyttades
   till 2026-0643, och offertrepot håller numren i ett gemensamt register, `.offertnummer.json`
   (laddbox 0640, elcentral 0641, batteri 0642, service 0643). Kontrollerat 24 okt mot de fem
   byggda sidorna: var och en visar sitt eget nummer och inget annat.
3. **Tilläggsoffertens eget nummer.** Finns inte. Brickan visar moderns referens.
   `offerter/tillagg/urval.json` `_kallor.moder`: inget ägarbeslut om formen.
4. **`moder.godkant_pris`** är `null`: priset kunden accepterade i moderofferten finns inte i
   repot, så bekräftelsen säger inget om det.
5. **Momsen.** Ingen momssats och inget momsbelopp finns någonstans i repot, bara brödtexten
   "inklusive moms". Frågan är dessutom tvetydig: ROT och grön teknik dras på det
   momsinklusive priset, så moms på brutto och moms på netto är två olika tal. Kontraktet har
   därför **inget momsfält**, och sidan säger bara "inkl. moms".
6. **Bokare för batteri, service och tillägg.** Batteri och service pekar båda på Rasmus med
   en notering om att namnet är en parameter per offert. Tillägget har ingen, och elektrikerns
   namn finns inte i repot.
7. **Är servicemallen planerat flöde eller akut eljour?** Styr steg 2 och 3. Är den
   akutflödet lovar steg 3 ett lugnt schema till någon som har strömavbrott.
8. **Ö-driftens pott.** Byggd som grön teknik efter principen i ägarbeslut 11 (15 okt). Är
   den brutto utan avdrag ändras en rad i `exempel/batteri.json`.
9. **Servicepriset 7 400 kr är ett exempel**, inte ett Ampy-pris
   (`offerter/service/jobb.json` `_kallor.pris`).
10. **Giltighetsdatum på den accepterade sidan.** Står fortfarande inte här, och ska inte göra
    det: offerten har ingen giltighetstid (ägardirektiv 23 okt). Fältet `giltig_till_lang` finns
    för avböjsskärmens tvilling, är `null` i alla fem kontrakten, och `prov.py` stoppar bygget om
    det sätts. Acceptdatumet är något annat och är inte gated på det här.
12. **Acceptdatumet saknas i alla fem fallen.** Ägarsvar 46 är byggt: fältet finns, sidan
    renderar det, oraklen provar både att det syns rätt och att en tom eller omöjlig uppgift
    stänger. Men **inget av de fem exemplen är accepterat av någon**, och ett acceptdatum uppstår
    i det ögonblick kunden trycker. Det finns därför inte i offertrepot, och de fem kontrakten bär
    `null`: de byggda sidorna visar ingen datumrad. Vill ägaren se raden på en sida behövs ett
    datum per fall, och då fylls `offert.accepterad`. Ingenting hittas på.
11. **Transporten finns inte.** Accepten skickas ingenstans, och bekräftelsen hämtar
    ingenting. Så länge det gäller är den här sidan en läsare utan något att läsa i
    produktion. Det är det enda som står mellan kontraktet och en fungerande orderbekräftelse.

**`ARBETSANDEL` 0,8 är inte längre ett `[GAP]` med konsekvens här.** Ingenting i det här
kontraktet härleds ur den, eftersom inget avdrag räknas eller visas.
