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

  "kostnader_ingress": "Behövs mer än standardinstallationen kostar det exakt så här. Allt bekräftas och godkänns av dig innan arbetet utförs.",
  "kostnader": [
    { "namn": "Extra installationskabel, 22 kW", "belopp": 245,  "enhet": "per meter", "text": null },
    { "namn": "Löpande arbete",                  "belopp": 850,  "enhet": "per påbörjad timme", "text": null },
    { "namn": "Felsökning av jordfel.",          "belopp": null, "enhet": null, "text": "Vid installation av jordfelsbrytare kan ..." }
  ],
  "kostnader_fot": "Priserna är inklusive moms. Avdraget räknas som i offerten: grön teknik på laddpunkten, ROT på elcentralen.",

  "forberedelser": [
    "Om du har valt lastbalansering som ansluts via elmätarens HAN-port behöver du ..."
  ],

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
| `kostnader` | lista | nej | **folden "Kostnader som kan tillkomma" visas inte alls** | mallen. Laddbox sju rader, batteri nio, elcentral tre villkorstexter utan pris. Service och tillägg: ingen. |
| `kostnader_ingress` | sträng | folden står utan ingress | mallen |
| `kostnader_fot` | sträng | folden står utan finstilt | mallen. Bara laddbox och batteri har en. |
| `forberedelser` | lista med strängar | **folden "Vad behöver du göra före installationen?" visas inte alls** | mallen. Laddbox, elcentral, batteri och **service** (ägarsvar 15, 30 oktober). Tillägg: ingen. |
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
| `giltig_till_lang` | sträng, t.ex. "27 oktober 2026" | meningen renderas **utan datum**. Aldrig en platshållare, aldrig ett gissat datum. | CRM. **INGEN YTA LÄSER FÄLTET LÄNGRE, mätt 30 oktober.** Noten sa att avböjsskärmens tvilling använder det (`skarm-avboj.html` rad 40). Det var sant till den 23 oktober, när ägaren svarade "Nej, ingen giltighetstid" och meningen togs ur blocket; den 30 oktober togs hela stegremsan ur avböjsskärmen på ägarsvar 11, ordagrant "Ta även bort den". Uppmätt samma dag: noll träffar på `giltig` i `gemensamt/block/skarm-avboj.html`, i `skarm-accept.html` och i de byggda `service.html`, `elcentral.html` och `tillagg.html`, och noll på "27 oktober 2026" i `offerter/elcentral/offert.py` (`str.replace`-bytet som noten citerade finns inte kvar). Fältet står med flit kvar som `null` i alla fem kontrakten, **så att ingen hårdkodar ett giltighetsdatum den dag det kommer tillbaka**, och `prov.py` stoppar bygget om det sätts. Att en not pekar på en rad i ett ANNAT repo är precis varför den hann bli falsk: ingen mätning här läser den filen. |
| `accepterad` | sträng, ISO 8601, t.ex. `"2026-10-25"` | **ingen mening skrivs**. Aldrig en platshållare, aldrig ett gissat datum, och ordet "Accepterad" står inte där ensamt. | CRM, i det ögonblick kunden trycker acceptera. **ÄGARSVAR 46, 25 oktober: "Ja, lägg till datum."** Sidan skriver den svenska formen ("25 oktober 2026") ur ISO-datumet, så de fem mallarna inte kan visa fem former; `prov.py` skriver samma form själv i stället för att läsa sidans. Ett datum som inte finns i kalendern (2026-02-30) **stänger totalen**: ett kontrakt som har fel om datumet är ett kontrakt som har fel, och sidan väljer inte vilka fel den bryr sig om. **Ett acceptdatum drar inte med sig ett `giltig till`:** offerten har ingen giltighetstid (ägardirektiv 23 okt), och `prov.py` stoppar varje sida som skriver ett. |
| `villkor_url` | URL | **ingen länk renderas, aldrig ett tomt `href`**, och villkorssektionen står kvar dold | CRM. `https://ampy.se/kopvillkor`, kontrollerad 19 okt, samma adress alla fem mallarna länkar till. Länktexten är deras, ordagrant: "Läs våra köpvillkor". **ÄGARENS GLOBALA NOTERING 25 OKTOBER:** länken ligger i en fold som heter **Villkor längst ner** på bekräftelsen, i samma form som offerternas egen villkorsfold (`offerter/tillagg/body.html` rad 60 till 67), inte längre i finstilten under raderna. På papper öppnas folden och adressen skrivs ut efter länken, så villkoren når papperet: en stängd fold döljer sitt innehåll genom `::details-content`, och det biter ingen display-regel på barnet. |

### `bokare` och `steg` är BORTTAGNA, 29 oktober

**ÄGARORDER 29 OKTOBER, ORDAGRANT:**

> "SÅHÄR GÅR VI VIDARE och alla dess 1/2/3 steg och copy tar vi bort helt och hållet från
> alla acceptera mallarna."

Beslutet togs i mötet samma dag. Ordagrant därifrån: *"de har ju accepterat offerten... Din
offert är nu accepterad. Ja, men det kanske räcker."* Och skälet: *"för oss pingar det ju till
så fort en offert är godkänd. Sen tar ju vi action på det. Jag tror inte många är så här, jaha,
nu då. De kommer ju få en bokningsbekräftelse snart."*

Båda fälten fanns **bara** för stegremsan. `steg` skrev över stegens copy, och `bokare.fornamn`
satte namnet i steg 2. Med remsan borta har de inget att fylla, och ett fält i ett kontrakt som
ingenting läser är ett påstående om att något renderas.

**En bekräftelse lovar inte en tid.** Det är bokningsbekräftelsens jobb, och den skickas ur
CRM:et med datum, klockslag och elektrikerns namn. Sidan som säger "Rasmus ringer och bokar tid"
ger ett löfte som ingen på Ampy har gett den dagen.

`prov.py` vaktar åt andra hållet: `samma-mall` kräver att **ingen** av de fem har en steglista,
och mutationen "29 okt, stegremsan tillbaka på en sida" bevisar att kravet faller. Kravet är
alltså inte raderat utan vänt.

Det som gick med dem: servicemallens två tal i steg 2 ("24 till 72 timmar"), som var de enda
talen i remsan. `talen.py`-golvet följde med, från 30 till 28, och sedan upp till 44 när
kostnadsfolden kom till.

### `kostnader`, `kostnader_ingress`, `kostnader_fot`

**ÄGARDOKUMENT 29 OKTOBER**, "Bokningsbekräftelse & Godkänd offert", ordagrant:

> "Det vi behöver lägga till är ovanför villkor. **1: Kostnader som kan tillkomma (som en
> dropdown) hämtas från offert mall laddbox.**"

Folden ligger ovanför villkoren, i samma form som villkorsfolden. Innehållet kommer ur
kontraktet och komponeras aldrig på sidan, för de fem mallarna säger olika saker.

| Fält | Typ | Betyder |
|---|---|---|
| `namn` | sträng | radens etikett, **ordagrant** ur offertmallen |
| `belopp` | heltal eller `null` | priset. `null` betyder att raden är en **villkorstext utan pris** |
| `enhet` | sträng eller `null` | "per meter", "per styck", "per påbörjad timme". Sidan skriver `kr(belopp) + " " + enhet` |
| `text` | sträng eller `null` | meningen efter namnet, **bara** på villkorstexter |

**Två former, för de två mallsorterna säger olika saker.** Laddbox och batteri har prissatta
rader. Elcentralen har tre villkorstexter **utan pris**, på Felix besked 29 oktober: *"De ska
ersättas med de nya texterna och har ingen fast prissättning som de tidigare då svårare moment
som inte kan prissättas utan görs som tillägg på plats av elektriker."*

**Raden bär inget `avdrag`-fält och summeras aldrig.** Talen är styckpriser och villkor, inte
poster i ordern. Ett belopp i ett fält som ser ut som `order.rader[]` hade bjudit in nästa
läsare att räkna med det.

**Varje `belopp` har en källa.** `verktyg/talen.py` slår upp det i
`katalog/tillkommande.json#rader[namn=X].pris` i offertrepot vid varje körning, så ett pris som
rör sig där gör det här provet rött. Första versionen 29 oktober lade "245 kr per meter" i ett
`text`-fält, och då provades ett **pris** som om det vore copy; `verktyg/ordagrant.py` såg det
direkt.

**ÄGARDIREKTIV 29 OKTOBER:** priset för en bomkörning eller en ombokning skrivs aldrig där
kunden ser det, bara i köpvillkoren.

### `forberedelser`

**ÄGARDOKUMENT 29 OKTOBER**, samma avsnitt:

> "**2: Vad behöver du göra innan installationen?** Här vill vi sätta en standard för laddbox,
> batteri och elcentral. Eftersom detta skiljer sig från produkt och offert."

En lista med strängar, en per punkt, **ordagrant** ur ägarens dokument. Texten ligger i
offertrepots `katalog/forberedelser.json` och är identisk tecken för tecken;
`verktyg/ordagrant.py` kontrollerar det.

**Den raden var falsk i ett dygn, och det är mätt.** `ordagrant.py` gick bara in i de listor
som stod namngivna i dess `STRANGLISTOR`, och där stod bara `ingar`. Fältet är en lista med
bara strängar, så de **tolv punkterna** på laddbox, elcentral och batteri provades aldrig en
enda gång mot offertrepot, från den dag folden byggdes 29 oktober till den 30:e. Verktygets
egen kommentar beskriver precis det felet för `ingar` och slutar med *"en lista vars poster är
kundtext ska namnges, annars provas nästa lista inte heller"* — och nästa lista provades inte
heller. Rättat: `forberedelser` står i mängden, antalet kontrollerade strängar gick från 67
till 81, och tre mutationer (en härledd punkt, ägarens egen mening på service, ägarens punkt 2
på batteri) bevisar att provet faller.

**Listan är GLOBAL per produkt och villkoras inte av kundens val.** Ägarbeskedet i mötet, om
laddboxen: *"den ska vara global. Den ska visas på alla oavsett vilken laddbox det är, oavsett
om de har valt lastbalansering eller inte."* Därför börjar punkten om lastbalansering med "Om du
har valt", vilket är ägarens egen formulering och lösningen på samma sak.

**Laddbox, elcentral, batteri och service har den. Tillägget har ingen**, och då står
sektionen kvar dold: en rubrik som lovar innehåll som inte finns är värre än ingen rubrik.
`prov.py` kräver att sektionen är dold precis när fältet saknas, och mutationerna bevisar det
åt båda håll.

**SERVICE FICK SIN DEN 30 OKTOBER, OCH DEN ÄR HÄRLEDD, INTE SKRIVEN.** Ägarsvar 15, ordagrant,
på frågan om service som bokats ur en godkänd offert ska ha en egen förberedelsetext:

> "Den ska baseras på arbete/material kolummnen som alltid används, oavsett om den är offert
> eller direktbokad."

De tre produkttexterna är ägarens egna ord, punkt för punkt. Servicens är två punkter som
**räknas fram** ur arbete- och materialkolumnen (`offerter/service/jobb.json` `jobb.rader`,
det CRM:et kallar "Arbete + Material") vid varje bygge i offertrepot: punkt 1 är katalogens
inledande sats plus kolumnen ordagrant, punkt 2 är ägarens egen mening, ordagrant densamma som
står sist i laddboxens och batteriets listor. Skälet att den härleds är ägarens eget:
servicemallen är **restmängden** (ägarbeslut 11, 26 oktober), så det finns ingen uppräknad
tjänsteflora att skriva en standardtext för, och kolumnen är det enda som ALLTID finns i båda
fallen han nämner. Fältet här är därför en **avskrift av en härledning**, och
`verktyg/ordagrant.py` är det som håller de två repona överens: ändras kolumnen i offertrepot
blir raden här röd.

Den inledande satsen "Arbetet i din bokning är:" är **inte ägarens ord utan mina**, och den
står flaggad i offertrepots `katalog/forberedelser.json` (`service._inledning_gap`). Ägarsvar
15 ger regeln, inte orden.

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

**En sträng. Inget annat.** Renderas med samma bock som varje punktlista i offerten
(`gemensamt/bitar.py` rad 10). Serviceofferten är den enda mall som inte konfigurerar något:
kunden läser en lista och svarar ja eller nej, och då **är** listan ordern.

Fram till 25 oktober fick en post också vara `{ "text": "...", "spec": "..." }`, och specen
renderades som en rad brödtext under punkten. **ÄGARENS ORD 25 OKTOBER, ordagrant:** *"Det
viktiga med allt som ingår är att om vi kollar på servicemallen så har vi till exempel byte av
sex strömbrytare, och sen har vi en text under det. Här ska det, och jag vet att det här var
feedback tidigare, bara vara en punktlista."* Och skälet är inte bara smak, samma pass om
offertens egen lista: *"vi kommer inte kunna göra det i praktiken, utan vi kommer bara ha
rubrikerna"*. Fältet är borttaget och inte bara orenderat: `prov.py` stoppar bygget på ett
objekt i listan, och renderaren flaggar det som ett kontraktsfel som stänger totalen.

### `order.utestaende[]`

Ett löfte offerten gav och som bekräftelsen ska kvittera.

| Fält | Typ | Betyder |
|---|---|---|
| `text` | sträng | radens etikett, t.ex. "Grannrabatt, 3 grannar inbjudna" |
| `ord` | sträng | står där beloppet annars stått, t.ex. "dras när de beställt" |

**Texten skrivs av den mall som gav löftet, ordagrant.** Sidan komponerar ingenting här.
Grannrabattens två strängar står i `offerter/laddbox/skript.js`.

**Fältet `not` är borttaget 25 oktober.** Det bar noten under listan, och på laddboxfallet löd
den *"Upp till 1 500 kr av, 500 kr för varje granne som beställer. Ditt pris här ändras inte
förrän det hänt."* **ÄGARENS ORD, ordagrant**, om hela texten under raderna: *"Här vill jag att
vi använder följande **enbart**: 'inkl. moms, efter skattereduktion. Avdragen dras direkt på
fakturan.'"* Blocket under raderna är därmed **en mening och ingenting mer**. Raden själv står
kvar och säger fortfarande att rabatten inte är dragen ("dras när de beställt"), så kvittensen
lovar inget den inte håller. Med strängen gick också dess två poster i `_tal`
(`.order.utestaende[0].not#500` och `#1500`, som band taket 1 500 kr till de tre inbjudna
grannarna): `verktyg/talen.py` stoppar bygget om en post bevakar ett tal som inte längre finns.

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
| 10 | Bara rader **med ett belopp** sätter en pott | en intresseanmälan dras inte och ska inte få finstilten att nämna en pott den inte hör till |
| 11 | **Ingen rad bär en pottmärkning**, oavsett hur många potter ordern har | ÄGARENS ORD 25 OKT: "Bara rubrikerna och priset." Vänt 25 oktober: här stod motsatsen, att varje prisrad märks när ordern har två potter. Den regeln gäller **offerten** (`offerter/tillagg/offert.py` rad 287 till 292), där kunden väljer, inte bekräftelsen, där hon redan valt. Radens **spec** står kvar: "i stället för 5 meter" säger vad kunden får |
| 12 | `accepterad` är `null` eller ett datum som finns i kalendern | inget totalbelopp, och ingen mening om datum |
| 13 | **En accepterad offert, en bekräftelse, ett nummer.** Sidan visar exakt ETT offertnummer, och det är kontraktets eget. Radlistan är exakt kontraktets egna rader. | provet stoppar bygget |
| 14 | **Varje tal kunden ser är härlett ur offertrepots egna källfiler**, med källan per operand i `_tal` | provet stoppar bygget |

Felen hamnar i `data-oa-fel` på `.oa` och i konsolen. Kunden ser bara att ett tal uteblev.

Finstilten under raderna och den korta satsen i kvittot byggs av `pottrad()`, **ordagrant
porterad** ur `offerter/tillagg/offert.py:pottrad`. Funktionen, inte ett radnummer: raderna
flyttar sig och en hänvisning till rad 162 pekade på något annat inom ett dygn. En mening om
moms och avdrag får inte finnas i två versioner i två repon.

**Ägarens lydelse, 25 oktober, ordagrant, i två meningar:**

| var | lydelse |
|---|---|
| kvittonoten under "Att betala" | *"inkl. moms, efter skattereduktion"* |
| finstilten under raderna | *"inkl. moms, efter skattereduktion. Avdragen dras direkt på fakturan."* |

Hans egna ord: om kvittonoten, *"Under att betala längst upp står även: 'inkl. moms, efter
skattereduktion (Grön teknik och ROT)'. Här vill jag att vi har: 'inkl. moms, efter
skattereduktion'."* Och om texten under raderna, *"Här vill jag att vi använder följande
**enbart**: 'inkl. moms, efter skattereduktion. Avdragen dras direkt på fakturan.'"*

**Parentesen är borta, och med den tre saker.** (1) Den korta satsen är nu ord för ord
offertrepots egen fasta text (`gemensamt/block/skarm-accept.html` rad 25), så de två ytorna
inte längre kan säga olika om samma sak; `verktyg/jamfor-skarm.py` mäter det. (2) Meningen är
densamma på alla fem. Förut sa elcentralen "(ROT)", batteriet "(Grön teknik)" och laddboxen
"(Grön teknik och ROT)", alltså tre lydelser på fem sidor, och det var en av de skillnader
ägaren såg när han sa att varenda mall är lite annorlunda. (3) "Avdragen" är ägarens egen form
och böjs inte längre efter antalet potter: utan uppräkning finns inget att kongruera med.
**Har ordern ingen pott alls står bara "inkl. moms"**: en bekräftelse utan skattereduktion får
inte nämna en. **Och "Rader utan avdrag är märkta." utgår med märkningen.** En mening som
beskriver en märkning som inte finns är en osanning, inte en överflödig rad. **Meningen "ROT förutsätter att du har avdragsutrymme kvar." står inte här, och kan inte
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

## 4b2. En mall, en skillnad

**ÄGARSVAR 25 OKTOBER, ORDAGRANT:** *"När jag har gått igenom mallarna ser jag att varenda
mall är lite annorlunda. Det jag hade sagt är att jag gillar servicemallen mest. (...)
Orderbekräftelsen kommer inte att ha olika mallar. Det enda är ju tilläggsarbetet, eftersom
'Så här går vi vidare' är annorlunda. Det är egentligen den enda skillnaden."*

**UNDANTAGET FÖLL BORT 29 OKTOBER, och mätningen blev strängare av det.** Ägarordern samma dag
tog bort stegremsan från alla fem. Fanns ingen steglista kvar finns inget att undanta, och
ägarens egen mening blir sann **utan förbehåll**: alla fem sidorna är nu samma tecken, med noll
undantag. `samma-mall` kräver dessutom att ingen av dem HAR en steglista, så kravet är vänt och
inte raderat. De två nya foldarnas kroppar blankas som data, precis som `oaRader` och `oaIngar`:
att de skiljer sig ÄR kontraktet. Att deras innehåll stämmer provas av `verktyg/ordagrant.py`
och `verktyg/talen.py`.

Det är ett påstående om **markup**, och det mäts därför i stället för att försäkras.
`verktyg/samma-mall.py` tar varje byggd sida, blankar det som är DATA och jämför resten
**tecken för tecken**:

* byggets huvudkommentar och `<title>` (tilläggsmallen byter flikrubriken ur kontraktet)
* `hidden` tas bort: att produktraden syns på laddboxen och inte på servicen är kontraktets
  `order.rubrik`, inte två mallar
* innehållet i de namngivna datafacken (`oaTitel`, `oaRefNr`, `oaAcceptDatum`, `oaPaket`,
  `oaTotal`, `oaProdRubrik`, `oaProdUnder`)
* radlistan och ingår-listan blir en markör: deras längd är ordern
* steglistan lyfts ut och jämförs för sig, med sin egen text blankad

**Vad som avsiktligt INTE blankas:** `oaFin`, `oaKvittoNot` och villkorsfoldens kropp står
kvar med sin text. Det var där mallarna drog isär, och efter 25 oktober säger alla fem samma
mening. Då ska den jämföras, inte blankas bort.

**Måttet är tvåsidigt.** Allt utanför steglistan ska vara samma tecken på alla fem, och exakt
**tilläggsmallens** steglista ska skilja sig. Slutar tillägget byta sin steglista är det lika
fel som att en annan mall börjar byta sin.

**Uppmätt 25 oktober, efter passet:** ett skelett för alla fem, och `['tillagg']` är hela
listan över mallar vars steglista skiljer sig. Före passet gav samma mätare fem olika
skelett: pottmärkningarna på raderna (laddbox och tillägg), noten under raderna (laddbox),
specerna under ingår-punkterna (service) och tre olika finstiltsmeningar.

**Produktraden och "Allt som ingår" är DATA, inte mallar.** Service och tillägg har ingen
produkt (`order.rubrik: null`), och bara service fyller `order.ingar`. Att ge de övriga en
ingår-lista, eller att ta bort "Zaptec Go" från laddboxens bekräftelse, hade krävt att något
hittades på eller att en uppgift kunden betalat för ströks. **`[GAP]`:** vill ägaren att
produktraden försvinner från alla fem är det ett fält i fem kontrakt, inte en ändring i
markupen, och det är hans beslut.

---

## 4b3. Villkoren bor i en fold längst ner

**ÄGARENS ORD 25 OKTOBER, GLOBAL NOTERING, ordagrant:** *"Under det har vi köpvillkor. Likt
hur vi har det i offerten hade jag velat att denna länk och 'Läs våra köpvillkor' ligger under
en dropdown som heter villkor som ligger längst ner på orderbekräftelsen (GLOBAL NOTERING)"*

Formen är **offertens egen**, inte en ny: en `o-fold` med rubriken Villkor och länken i
kroppen står likadant i `offerter/laddbox/body.html`, `elcentral/body.html`,
`batteri/body.html` och `tillagg/body.html`. Måtten är deras (`gemensamt/system.css` rad 170
till 178) och ligger redan på den här sidans skalor, så inget nytt mått uppstår av flytten.

**Placeringen speglar offerten:** folden är sista innehållsblocket, och under den står
kortets avslutning med telefonnumret, precis som offertens `<footer class="o-fot">` står under
folden där. `prov.py` mäter att villkorssektionen är **näst sist** bland sektionerna.
**`[GAP]`:** menade ägaren bokstavligen efter telefonnumret är det en flytt på en rad.

**Länken skrivs av renderaren, inte av markupen.** Ett tomt `href` är inget villkor: saknas
`villkor_url` står sektionen kvar dold. Och den står på **ett** ställe: `prov.py` räknar
"Läs våra köpvillkor" och kräver exakt en förekomst, så den inte kan bli kvar i finstilten
också.

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
| `kostnader` | 7 prissatta rader | 3 villkorstexter utan pris | 9 prissatta rader | ingen | ingen |
| `forberedelser` | 5 punkter | 2 punkter | 5 punkter | **2 punkter, härledda** | ingen |
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
6. ~~**Bokare för batteri, service och tillägg.**~~ **STÄNGD 29 oktober** när stegremsan togs
   bort: det fanns ingen annan yta som namngav bokaren, så frågan har inget svar att ge.
   Elektrikerns namn hör nu hemma i bokningsbekräftelsen, som skickas ur CRM:et.
7. ~~**Är servicemallen planerat flöde eller akut eljour?**~~ **STÄNGD 29 oktober av samma
   skäl**: frågan styrde steg 2 och 3, och de finns inte längre. Den kan komma tillbaka som en
   fråga om bokningsbekräftelsens copy, men inte om den här sidan.
7b. ~~**Ska service som bokats ur en godkänd offert ha en egen förberedelsetext?**~~
   **STÄNGD 30 oktober.** Ägarsvar 15, ordagrant: *"Den ska baseras på arbete/material
   kolummnen som alltid används, oavsett om den är offert eller direktbokad."* Byggd som en
   HÄRLEDD text, se `forberedelser` ovan. Kvar som en liten lucka: den inledande satsen
   "Arbetet i din bokning är:" är mina ord, inte ägarens, och står flaggad i offertrepots
   `katalog/forberedelser.json` (`service._inledning_gap`).
8. **Ö-driftens pott.** Byggd som grön teknik efter principen i ägarbeslut 11 (15 okt). Är
   den brutto utan avdrag ändras en rad i `exempel/batteri.json`.
9. **Servicepriset 7 400 kr är ett exempel**, inte ett Ampy-pris
   (`offerter/service/jobb.json` `_kallor.pris`).
10. **Giltighetsdatum på den accepterade sidan.** Står fortfarande inte här, och ska inte göra
    det: offerten har ingen giltighetstid (ägardirektiv 23 okt). Fältet `giltig_till_lang` finns
    för avböjsskärmens tvilling, är `null` i alla fem kontrakten, och `prov.py` stoppar bygget om
    det sätts. Acceptdatumet är något annat och är inte gated på det här.
12. ~~**Acceptdatumet saknas i alla fem fallen.**~~ **PROVAT 25 oktober.** Ägarsvar 46 är
    byggt: fältet finns, sidan renderar det, oraklen provar både att det syns rätt och att en
    tom eller omöjlig uppgift stänger. Ägaren bad om ett prov, och det finns nu som ett
    **provfall**: `exempel/prov-acceptdatum.json` och `fall/prov-acceptdatum.html`. Provfallet
    är `exempel/laddbox.json` **tecken för tecken, med exakt ett fält ändrat**
    (`offert.accepterad`), och `prov.py` mäter just det, plus att den byggda sidan skiljer sig
    från `fall/laddbox.html` i **exakt två rader, båda acceptraden**. Det gör provfallet
    ofarligt: det kan inte visa ett tal eller en sträng som laddboxsidan inte redan visar.
    **De fem riktiga fallen bär fortfarande `null` och ska göra det**, för inget av dem är
    accepterat av någon, och `prov.py` stoppar bygget om ett av dem får ett datum. Datumet i
    provfallet är ett **provvärde**, inte ett påstående om någon kund. Ingenting hittas på.
11. **Transporten finns inte.** Accepten skickas ingenstans, och bekräftelsen hämtar
    ingenting. Så länge det gäller är den här sidan en läsare utan något att läsa i
    produktion. Det är det enda som står mellan kontraktet och en fungerande orderbekräftelse.

**`ARBETSANDEL` 0,8 är inte längre ett `[GAP]` med konsekvens här.** Ingenting i det här
kontraktet härleds ur den, eftersom inget avdrag räknas eller visas.
