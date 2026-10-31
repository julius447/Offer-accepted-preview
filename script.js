/* =========================================================================
   Ampy orderbekräftelse — renderaren

   Sidan är kundens KVITTENS på en accepterad offert, och den ska bära samma
   order för alla fem offertmallarna: laddbox, elcentral, batterilagring,
   service och tilläggsoffert. Allt den visar kommer ur ETT kontrakt,
   window.AMPY_ORDER, som är beskrivet fält för fält i KONTRAKT.md.

   TVÅ VÄGAR, EN SANNING.
   1. Serversidan renderar värdena direkt i markupen (SSR). Då är det här
      skriptet en no-op, och sidan fungerar med JavaScript avstängt. Det är
      den väg som gäller i produktion: en accepterad order är en handling
      kunden sparar och skriver ut.
   2. Serversidan skriver ut window.AMPY_ORDER i sidan och skriptet fyller.
      Samma mekanism som förut, bara med ett kontrakt som bär hela ordern.
   Filerna i fall/ är byggda väg 2 och sparade som väg 1, så de är samma sak.

   ALDRIG URL-parametrar och ALDRIG localStorage. Priser och radinnehåll i en
   query-sträng är manipulerbara och hamnar i loggar och referrers, och kunden
   öppnar bekräftelsen i mejlet på en annan enhet än den där hon accepterade.
   Ordern bor i CRM:et. Sidan är en läsare.

   INGEN TRANSPORT HÄRIFRÅN. Ingen fetch, ingen XMLHttpRequest, ingen
   sendBeacon, inget formulär. Skärmen säger att accepten är registrerad, och
   det löftet hålls av servern som renderar sidan, inte av den här filen. Det
   är ett erkänt gap i offertrepots META och den här sidan lägger inte till
   nya löften om leverans.

   FEL I KONTRAKTET STÄNGER, DET GISSAR INTE.
   Går raderna inte ihop med totalen renderas inget totalbelopp alls. Bär en
   rad en avdragspott som inte finns i vokabulären renderas inget totalbelopp
   alls, för då går finstilten om moms och avdrag inte att skriva sant. Saknas
   ett värde skrivs meningen utan det: aldrig en platshållare, aldrig ett
   gissat datum, aldrig ett tomt href.

   ETT ROT-BELOPP SKRIVS ALDRIG UT. Ägardirektiv 2026-10-23, i versaler:
   "VI KOMMER ALDRIG SKRIVA UT HUR MYCKET ROT AVDRAGET PÅ ELCENTRAL UPPGÅR
   TILL. VI VISAR BARA TOTALSUMMAN SOM ÄR PRISET EFTER ROT INKL MOMS."
   Kontraktet har därför inget fält för ett avdragsbelopp, och sidan räknar
   inget avdrag. Alla belopp är netto: efter avdrag och inklusive moms.
   ========================================================================= */
(function () {
  'use strict';
  var root = document.querySelector('.oa');
  if (!root) return;

  function $(id) { return document.getElementById(id); }

  /* ETT TAL, ETT TECKEN. Hårdspatie (U+00A0) BÅDE mellan tusentalen OCH före
     kr. ÄGARBESLUT 24 oktober (A8): ett vanligt mellanslag tillåter radbrytning
     mitt i beloppet, så "14 345" kan hamna på en rad och "kr" på nästa.
     UPPMÄTT FÖRE: alla 24 beloppen på de fem byggda sidorna bar vanligt
     mellanslag före kr. Samma rad som laddboxrepots KR_JS,
     offerter/elcentral/offert.py rad 177 och offerter/service/offert.py rad 117.
     toLocaleString ger olika avgränsare i olika webbläsare, och ett tal som ser
     olika ut på två ställen läser som två olika tal. */
  function kr(n) {
    return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + ' kr';
  }

  /* ---- AVDRAGSVOKABULÄRET. Tre värden, inte fyra stavningar. -------------
     katalog/tillval.json har hetat gron-teknik | rot | inget hela tiden, och
     det är den fil gemensamt/orakel.py redan läser. Elcentralens "gt" och
     laddboxmarkupens data-rot-boolean mappas HIT av den som fyller
     kontraktet, inte av den här sidan: tar sidan emot fyra stavningar lever
     fyra stavningar vidare. Ett okänt värde stänger totalen. */
  /* INGEN ETIKETT. Vokabulären är en LISTA, inte en etiketttabell.
     ÄGARENS ORD 25 OKTOBER, ORDAGRANT: "Jag vill bara att du ska ha själva
     rubrikerna, 'i stället för 5 meter' och inte 'grön teknikavdrag', utan
     det gör bara så att det här blir ännu mer klotterigt. Bara rubrikerna
     och priset."
     Potten styr fortfarande finstilten, och ett okänt värde stänger
     fortfarande totalen: skillnaden är att den inte längre SKRIVS vid raden.
     Etiketterna är borta ur koden och inte bara ur renderingen, för en
     tabell som finns kommer någon att rendera. */
  var POTT = ['gron-teknik', 'rot', 'inget'];

  /* Raden under totalen. ORDAGRANT porterad ur laddboxrepots
     offerter/tillagg/offert.py:pottrad. Samma ord i två repon: en mening om
     moms och avdrag får inte finnas i två versioner. Returnerar [kort, hel].
     Den korta satsen står i kvittonoten, den hela i finstilten, precis som
     tilläggsmallen gör.

     ÄGARENS ORD, D3 24 OKTOBER, ORDAGRANT:
         "inkl. moms, efter skattereduktion (Grön teknik och ROT).
          Avdragen dras direkt på fakturan."

     TRE SAKER BYTTES MOT DEN FÖRRA PORTEN, OCH ALLA TRE ÄR ÄGARENS:
     1. ORDET SKATTEREDUKTION FÖRST, potterna i parentes. Förut stod "efter
        grön teknik och ROT", alltså två programnamn utan överord.
        "Skattereduktion" är vad båda är, och det är Skatteverkets ord.
     2. POTTNAMNEN ÄR VERSALA i parentesen: "Grön teknik", inte "grön teknik".
        Ägarens egen skrivning.
     3. MENINGEN OM AVDRAGSUTRYMME UTGÅR. Ägaren tog bort den 24 okt, och
        tilläggsmallens eget orakel stoppar nu bygget om ordet står på sidan
        (offerter/tillagg/offert.py rad 382). Villkoret står kvar exakt EN
        gång i elcentral- och servicemallens egen finstilt, alltså i den
        OFFERT kunden läste innan hon accepterade; hedging-direktivet 15 aug
        säger EN gång, inte en gång per sida. ÄGARGRIND: vill ägaren ha
        tillbaka meningen på bekräftelsen är det en rad här och en i prov.py.

     PARENTESEN ÄR BORTTAGEN, ÄGARENS ORD 25 OKTOBER, ORDAGRANT. Om texten
     under raderna: "Här vill jag att vi använder följande enbart: 'inkl.
     moms, efter skattereduktion. Avdragen dras direkt på fakturan.'" Och om
     noten i kvittot: "Under att betala längst upp står även: 'inkl. moms,
     efter skattereduktion (Grön teknik och ROT)'. Här vill jag att vi har:
     'inkl. moms, efter skattereduktion'."

     TRE FÖLJDER AV ATT PARENTESEN GÅR BORT:
     1. DEN KORTA SATSEN ÄR NU ORD FÖR ORD OFFERTREPOTS FASTA TEXT. Den
        delade acceptskärmen inne i offerten säger exakt "inkl. moms, efter
        skattereduktion" (gemensamt/block/skarm-accept.html rad 25), och de
        två ytorna kan därmed inte längre säga olika om samma sak.
     2. MENINGEN ÄR DENSAMMA PÅ ALLA FEM. Förut sa elcentralen "(ROT)",
        batteriet "(Grön teknik)" och laddboxen "(Grön teknik och ROT)",
        alltså tre lydelser på fem sidor. Ägaren: "varenda mall är lite
        annorlunda."
     3. "Avdragen" ÄR ÄGARENS EGEN FORM och böjs inte längre efter antalet
        potter. Utan parentesen står ingen uppräkning kvar att kongruera med,
        och en bekräftelse med flera avdragna rader har avdrag i plural
        oavsett om de hör till en pott eller två.

     UTAN AVDRAG STÅR BARA "inkl. moms". Den grenen är inte dekoration: en
     order där varje rad bär potten "inget" har ingen skattereduktion, och
     ägarens mening hade då varit osann. Finns ingen pott nämns ingen.
     "Rader utan avdrag är märkta" UTGÅR MED MÄRKNINGEN. Den meningen var
     sann så länge raderna bar en pottetikett. Nu gör de inte det, och en
     mening som beskriver en märkning som inte finns är en osanning, inte
     en överflödig rad. */
  function pottrad(potter) {
    var harAvdrag = potter.indexOf('gron-teknik') >= 0 || potter.indexOf('rot') >= 0;
    if (!harAvdrag) return ['inkl. moms', 'inkl. moms.'];
    var forsta = 'inkl. moms, efter skattereduktion';
    return [forsta, forsta + '. Avdragen dras direkt på fakturan.'];
  }

  /* ---- ACCEPTDATUMET. Ägarsvar 46, 25 oktober: "Ja, lägg till datum." ----
     Kontraktet bär ISO 8601 (2026-10-25), sidan skriver svenska. Tre skäl:

     1. ETT DATUM SKA SE LIKADANT UT PÅ FEM MALLAR. Samma skäl som kr():
        ett tal som ser olika ut på två ställen läser som två olika tal. Låg
        formen i datat hade fem CRM-fält kunnat ge fem former.
     2. toLocaleDateString ÄR INTE ETT SVAR. Den ger olika resultat i olika
        webbläsare och på olika språkinställningar, och en kund med engelsk
        telefon hade fått "October 25, 2026" på en svensk faktura. Tabellen
        nedan är fast och kan inte bero på var sidan öppnas.
     3. ISO GÅR ATT MÄTA. En färdigskriven sträng kan tyst vara "nästa vecka";
        ett ISO-datum kan provas mot kalendern, och prov.py skriver samma
        svenska form SJÄLVT i stället för att läsa sidans.

     ETT DATUM SOM INTE FINNS STÄNGER. 2026-02-30 ser riktigt ut i en regex
     men finns inte, så kalendern får svara. Kontraktet flaggas, och eftersom
     ett felaktigt kontrakt inte är en felstavning renderas inget totalbelopp
     heller: sidan väljer inte vilka fel den bryr sig om. */
  var MANADER = ['januari', 'februari', 'mars', 'april', 'maj', 'juni',
                 'juli', 'augusti', 'september', 'oktober', 'november', 'december'];
  function datumLang(v) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(v == null ? '' : v).trim());
    if (!m) return null;
    var ar = +m[1], man = +m[2], dag = +m[3];
    var d = new Date(Date.UTC(ar, man - 1, dag));
    if (d.getUTCFullYear() !== ar || d.getUTCMonth() !== man - 1 || d.getUTCDate() !== dag) return null;
    return dag + ' ' + MANADER[man - 1] + ' ' + ar;
  }

  /* EN BOCK, INTE TVÅ. Samma vektor som varje punktlista i offerten,
     gemensamt/bitar.py rad 10 till 11. */
  var BOCK = '<span class="oa__bock" aria-hidden="true"><svg viewBox="0 0 12 12">'
           + '<path d="M2.6 6.45 4.7 8.65 9.4 3.85"/></svg></span>';

  function txt(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function str(v) { return (typeof v === 'string' && v.trim()) ? v.trim() : null; }
  function tal(v) { return (typeof v === 'number' && isFinite(v)) ? v : null; }
  function visa(el, pa) { if (el) el.hidden = !pa; }

  /* ===================================================================== */
  var data = window.AMPY_ORDER;
  var platt = window.AMPY_OFFER;

  /* Det gamla platta objektet lever kvar: gemensamt/block/skarm-accept.html
     fyller data-oa="offert.referens" med det i dag. Bär sidan ett kontrakt
     härleds de platta nycklarna ur det, så de två vägarna inte kan säga olika.
     BOKARNAMNET ÄR BORTA HÄRIFRÅN 29 OKTOBER. Det fyllde data-oa="bokare.namn"
     i acceptskärmens steg 2, och steg 2 finns inte längre på någondera ytan.
     En härledning av ett fält som inte finns i kontraktet är ett tyst påstående
     om att det gör det. */
  if (data && typeof data === 'object') {
    var o = data.offert || {};
    platt = platt || {};
    if (platt['offert.referens'] == null && str(o.referens)) platt['offert.referens'] = str(o.referens);
    if (platt['offert.giltig_till_lang'] == null && str(o.giltig_till_lang)) platt['offert.giltig_till_lang'] = str(o.giltig_till_lang);
  }

  if (platt && typeof platt === 'object') {
    root.querySelectorAll('[data-oa]').forEach(function (el) {
      var k = el.getAttribute('data-oa');
      if (platt[k] != null && platt[k] !== '') el.textContent = platt[k];
    });
    root.querySelectorAll('[data-oa-href]').forEach(function (el) {
      var k = el.getAttribute('data-oa-href');
      if (platt[k]) el.setAttribute('href', platt[k]);
    });
  }

  if (!data || typeof data !== 'object') return;

  var offert = data.offert || {};
  var order  = data.order  || {};

  /* Felen samlas FRÅN FÖRSTA SEKTIONEN. Listan deklarerades tidigare nere vid
     ordern, och då hade ett fel i referensbrickan eller i acceptdatumet inte
     haft någonstans att ta vägen: var hissas, värdet gör det inte, så en
     push före raden hade kastat ett TypeError mitt i renderingen. */
  var fel = [];

  /* ---- 1 · REFERENSBRICKAN ---------------------------------------------
     En tilläggsoffert hänger på en offert kunden redan accepterat, och hon
     har redan ett nummer. Utan moderreferensen ser hon två orelaterade
     nummer. Samma formulering som tilläggsmallen själv bygger,
     offerter/tillagg/offert.py rad 226 till 227. */
  if (str(offert.titel)) {
    $('oaTitel').textContent = str(offert.titel);
    /* Flikrubriken och utskriftens sidhuvud ska saga samma sak som kortet.
       Mittpunkt och tankstreck ar bannade, darfor kommatecken. */
    document.title = str(offert.titel).replace(/!$/, '') + ', Ampy';
  }

  var ref = str(offert.referens), moder = str(offert.moderreferens);
  var arTillagg = offert.ar_tillagg === true;
  var visaRef = arTillagg ? moder : ref;
  if (visaRef) {
    $('oaRefEtikett').textContent = arTillagg ? 'Tillägg till offert' : 'Offert';
    $('oaRefNr').textContent = visaRef;
  }
  visa($('oaRef'), !!visaRef);

  /* NÄR hon accepterade. Ägarsvar 46. Saknas datumet står ingen mening alls:
     en tom rad "Accepterad" är sämre än ingen rad, och ett gissat datum på
     en bindande handling är det värsta av de tre. */
  var acceptLang = datumLang(offert.accepterad);
  if (offert.accepterad != null && offert.accepterad !== '' && !acceptLang) {
    fel.push('accepterad är inget datum i kalendern: ' + JSON.stringify(offert.accepterad));
  }
  if (acceptLang) {
    $('oaAcceptDatum').textContent = acceptLang;
    visa($('oaAccept'), true);
  }

  /* ---- 2 · STEGEN AR BORTTAGNA ----------------------------------------
     AGARORDER 29 OKTOBER, ORDAGRANT: "SAHAR GAR VI VIDARE och alla dess
     1/2/3 steg och copy tar vi bort helt och hallet fran alla acceptera
     mallarna." Beslutet togs i motet samma dag: "de har ju accepterat
     offerten... Din offert ar nu accepterad. Ja, men det kanske racker." Och
     skalet: "for oss pingar det ju till sa fort en offert ar godkand. Sen tar
     ju vi action pa det. De kommer ju fa en bokningsbekraftelse snart."

     DET TOG MED SIG TVA KONTRAKTSFALT. `steg` fanns bara for att skriva om
     stegen, och `bokare.fornamn` bara for att satta namnet i steg 2. Bada ar
     ute ur KONTRAKT.md med datum. En bekraftelse far inte lova ett samtal,
     en tid eller en ordning pa handelser: det ar bokningsbekraftelsens jobb,
     och den skickas ur CRM:et.

     prov.py vaktar at andra hallet, sa remsan inte kan komma tillbaka. */

  /* ---- 3 · ORDERN -------------------------------------------------------
     paket får vara null. Det är fallet service och tilläggsoffert: de har
     ingen paketlogik, bara rader. rader får vara tom, aldrig null. */
  var paket = (order.paket && typeof order.paket === 'object') ? order.paket : null;
  var rader = Array.isArray(order.rader) ? order.rader : [];
  var utest = Array.isArray(order.utestaende) ? order.utestaende : [];
  var ingar = Array.isArray(order.ingar) ? order.ingar : [];

  /* Alla belopp i kontraktet är netto: efter avdrag och inklusive moms.
     Fältet har ingen default med flit. Står det något annat där renderas
     inget belopp: det är EXAKT den konflikten som gjorde att samma lilla
     elcentral kostade 5 990 kr på laddboxsidan och 4 552 kr på
     elcentralsidan, och en bekräftelse som visar fel tal lämnar kunden med
     risken mot Skatteverket. */
  var netto = data.priser_ar === 'netto';

  if (!netto) fel.push('priser_ar är inte "netto"');

  /* Potterna HÄRLEDS ur raderna, de står inte i kontraktet. Ett fält som kan
     motsäga raderna är ett fält som kommer att motsäga raderna. Bara rader
     med ett belopp räknas: en intresseanmälan dras inte, så den sätter ingen
     pott och ska inte få finstilten att nämna en. */
  var potter = [];
  function pott(v, harBelopp) {
    var p = str(v);
    if (!p || POTT.indexOf(p) < 0) { fel.push('okänd avdragspott ' + JSON.stringify(v)); return null; }
    if (harBelopp && potter.indexOf(p) < 0) potter.push(p);
    return p;
  }

  var summa = 0, poster = [];
  if (paket) {
    var pb = tal(paket.belopp);
    var pp = pott(paket.avdrag, pb != null);
    if (pb != null) summa += pb;
    poster.push({ huvud: true, namn: str(paket.namn) || str(order.rubrik) || '',
                  under: str(paket.spec), pott: pp, belopp: pb, ord: null });
  }
  rader.forEach(function (r) {
    if (!r || typeof r !== 'object') return;
    var typ = str(r.typ) || 'tillagg';
    var belopp = tal(r.belopp);
    if (typ === 'intresseanmalan' && belopp != null) {
      fel.push('intresseanmälan med belopp: ' + str(r.namn));
      belopp = null;
    }
    var p = pott(r.avdrag, belopp != null);
    if (belopp != null) summa += belopp;

    /* ANTALET UT UR RADNAMNET. Laddboxmotorn bakar in "6 stycken" i strängen
       (radNamn, offerter/laddbox/skript.js rad 44 till 53), elcentralen håller
       det som eget fält. Kontraktet har antal och styckpris separat, annars
       kan bekräftelsen inte visa "6 x 800 kr". */
    var namn = str(r.namn) || '';
    if (str(r.variant)) namn += ', ' + str(r.variant);
    var under = [];
    var ant = tal(r.antal), styck = tal(r.styckpris);
    if (ant != null && ant > 1) {
      under.push(styck != null ? (ant + ' stycken, ' + kr(styck) + ' per styck') : (ant + ' stycken'));
    }
    /* MELLANSKILLNADEN MÅSTE MÄRKAS. En kabel som ingår i paketet är betald i
       5-metersutförande; väljer kunden 10 meter betalar hon skillnaden. En
       lista som skriver namn och belopp rakt upp säger att en laddkabel
       kostar 200 kr. offerter/laddbox/skript.js rad 218. */
    if (typ === 'mellanskillnad') {
      var ist = str(r.i_stallet_for);
      if (!ist) fel.push('mellanskillnad utan i_stallet_for: ' + namn);
      else under.push('i stället för ' + ist);
    }
    if (str(r.spec)) under.push(str(r.spec));
    poster.push({ huvud: typ === 'huvud', namn: namn, under: under.join(', ') || null, pott: p,
                  belopp: belopp, ord: belopp == null ? (str(r.notis) || 'ingen kostnad nu') : null });
  });

  /* EN RAD ÄR RUBRIKEN, SPECEN OCH PRISET. INGEN POTTMÄRKNING.
     ÄGARENS ORD 25 OKTOBER, ORDAGRANT: "Till exempel står det 'grön teknik'
     under paket Premium. Laddkabel 22 kilowatt, 10 meter. Då har du också
     lagt till 'i stället för 5 meter'. Och sedan också 'grön teknikavdrag',
     RFID-taggar 5-pack, 'grön teknikavdrag'. (...) Jag vill bara att du ska
     ha själva rubrikerna, 'i stället för 5 meter' och inte 'grön
     teknikavdrag', utan det gör bara så att det här blir ännu mer
     klotterigt. Bara rubrikerna och priset."
     SKILLNADEN MELLAN DE TVÅ UNDERRADERNA ÄR DÄRFÖR AVGÖRANDE OCH INTE EN
     SMAKSAK: "i stället för 5 meter" säger vad kunden FÅR, och utan den
     läser raden som att en laddkabel kostar 200 kr. "Grön teknik-avdrag"
     säger bara vilken skattekolumn raden hamnar i, och det säger finstilten
     redan en gång för hela ordern. Specen står kvar, märkningen går bort. */
  var html = poster.map(function (p) {
    var un = p.under ? '<small>' + txt(p.under) + '</small>' : '';
    var pris = (netto && p.belopp != null)
      ? '<span class="oa__rad-pris kr">' + txt(kr(p.belopp)) + '</span>'
      : (p.ord ? '<span class="oa__rad-pris oa__rad-pris--ord">' + txt(p.ord) + '</span>' : '');
    return '<li class="oa__rad' + (p.huvud ? ' oa__rad--huvud' : '') + '">'
         + '<span class="oa__rad-text">' + txt(p.namn) + un + '</span>' + pris + '</li>';
  });

  /* Utestående: ett löfte offerten gav och som bekräftelsen ska kvittera.
     Grannrabatten är det enda fallet i dag. Texten kommer ur den mall som
     gav löftet, ordagrant, och sidan skriver inget eget om den.
     INGEN NOT UNDER RADERNA. ÄGARENS ORD 25 OKTOBER om texten under
     grannrabattraden, ordagrant: "Här vill jag att vi använder följande
     ENBART: 'inkl. moms, efter skattereduktion. Avdragen dras direkt på
     fakturan.'" Noten "Upp till 1 500 kr av, 500 kr för varje granne som
     beställer. Ditt pris här ändras inte förrän det hänt." går därmed bort,
     och med den fältet `not`: ett fält som finns kommer någon att rendera.
     Raden själv står kvar och säger fortfarande att rabatten inte är dragen
     ("dras när de beställt"), så kvittensen lovar inget den inte håller. */
  utest.forEach(function (u) {
    if (!u || !str(u.text)) return;
    html.push('<li class="oa__rad"><span class="oa__rad-text">' + txt(str(u.text)) + '</span>'
            + (str(u.ord) ? '<span class="oa__rad-pris oa__rad-pris--ord">' + txt(str(u.ord)) + '</span>' : '')
            + '</li>');
  });

  $('oaRader').innerHTML = html.join('');

  /* PRODUKTRADEN RENDERAS INTE LANGRE, 31 OKTOBER, AGARORDER.
     Forlagan ar acceptskarmen (gemensamt/block/skarm-accept.html), och den
     har ingen produktrad: under kvittorutan star raderna och ingenting
     annat. Falten order.rubrik och order.underrubrik star KVAR i kontraktet
     med sin proveniens, av samma skal som offert.giltig_till_lang: ett falt
     som ingen yta laser far inte tystna, for da hardkodar nasta person det.
     prov.py kraver att ingen sida skriver dem. [GAP] Agaren kan vilja ha
     produktnamnet tillbaka i en lattare form; da finns talet kvar. */
  var rubrik = str(order.rubrik);

  /* "Allt som ingår." Serviceofferten är den mall som inte konfigurerar
     något: kunden läser en lista och svarar ja eller nej. Då är listan hela
     ordern och måste följa med på kvittensen.
     EN REN PUNKTLISTA, INGEN BRÖDTEXT UNDER PUNKTERNA. ÄGARENS ORD 25
     OKTOBER, ORDAGRANT: "Det viktiga med allt som ingår är att om vi kollar
     på servicemallen så har vi till exempel byte av sex strömbrytare, och
     sen har vi en text under det. Här ska det, och jag vet att det här var
     feedback tidigare, bara vara en punktlista."
     OCH SKÄLET ÄR INTE BARA SMAK. Samma pass, om offertens egen lista:
     "vi kommer inte kunna göra det i praktiken, utan vi kommer bara ha
     rubrikerna". Underraderna beskrev ett jobb ingen lovat så noggrant.
     En post är därför en STRÄNG och inget annat: tog listan emot ett objekt
     med ett spec-fält skulle nästa kontrakt fylla det. */
  if (ingar.length) {
    $('oaIngar').innerHTML = ingar.map(function (i) {
      if (i && typeof i === 'object') { fel.push('ingår-posten är ett objekt, inte en sträng'); return ''; }
      return str(i) ? '<li>' + BOCK + '<span>' + txt(str(i)) + '</span></li>' : '';
    }).join('');
    visa($('oaIngarRubrik'), true);
    visa($('oaIngar'), true);
  }

  /* ---- 4 · TOTALEN -----------------------------------------------------
     Invarianten: paketet plus raderna ÄR totalen. Går det inte ihop renderas
     inget totalbelopp alls. Ett tal som inte stämmer med raderna över det är
     värre än inget tal, för kunden kan inte se vilket av dem som är fel. */
  var total = tal(order.total);
  if (total != null && Math.round(total) !== Math.round(summa)) {
    fel.push('totalen ' + total + ' mot raderna ' + summa);
  }
  if (arTillagg && !moder) fel.push('ar_tillagg utan moderreferens');

  var kort = pottrad(potter);
  if (netto && total != null && !fel.length) {
    $('oaPaket').textContent = str(order.etikett) || 'Att betala';
    $('oaTotal').textContent = kr(total);
    $('oaKvittoNot').textContent = kort[0];
    visa($('oaKvitto'), true);
  }

  /* FINSTILTEN UNDER RADERNA AR BORTA, 31 OKTOBER, AGARORDER. Forlagan bar
     villkoret EN gang, som kvittorutans egen not (oa__kvitto-not), och
     hedging-direktivet 2026-08-15 sager just EN gang. Meningen stod till i
     dag pa BADA stallena: "inkl. moms, efter skattereduktion" i noten och
     "inkl. moms, efter skattereduktion. Avdragen dras direkt pa fakturan."
     i finstilten. Nu star den dar forlagan har den.
     [GAP] Satsen "Avdragen dras direkt pa fakturan." foll darmed bort fran
     sidan. Den ar agargodkand och star kvar i kort[1] i texterna, sa den
     kan laggas i noten om agaren vill ha den tillbaka. */

  /* ---- 4b · KOSTNADER SOM KAN TILLKOMMA ---------------------------------
     Agardokument 29 oktober: folden hamtas fran offertmallen och ligger
     ovanfor villkoren. INNEHALLET KOMMER UR KONTRAKTET och komponeras inte
     har, for de fem mallarna sager olika saker: laddboxen sju prissatta
     rader, batteriet nio, elcentralen tre villkorstexter UTAN pris (Felix 29
     okt: "svarare moment som inte kan prissattas utan gors som tillagg pa
     plats av elektriker"), och service och tillagg ingen fold alls.

     RADEN BAR INGET BELOPPSFALT, och det ar med flit. Ett tal i ett
     belopp-falt hade bjudit in nasta lasare att summera det, och de har
     talen ar styckpriser och villkor, inte poster i ordern. De ar text.

     Agardirektiv 29 oktober: priset for en bomkorning eller ombokning skrivs
     aldrig dar kunden ser det, bara i kopvillkoren. prov.py vaktar det. */
  var kost = Array.isArray(data.kostnader) ? data.kostnader : null;
  if (kost && kost.length) {
    var kh = '';
    var kIng = str(data.kostnader_ingress);
    if (kIng) kh += '<p class="oa__fold-intro">' + txt(kIng) + '</p>';
    /* TVA FORMER, for de tva mallsorterna sager olika saker.
       PRISSATT RAD: namn till vanster, belopp plus enhet till hoger. Beloppet
       formateras med sidans egen kr(), samma funktion som ordern anvander, sa
       ett belopp inte kan skrivas pa tva satt pa samma sida.
       VILLKORSTEXT: namn i fetstil och meningen efter, pa en rad som bryter.
       Elcentralens tre rader har inget pris alls (Felix 29 okt: "svarare
       moment som inte kan prissattas utan gors som tillagg pa plats"), och
       ett tomt belopp far inte bli "0 kr". */
    kh += '<ul class="oa__fold-lista">';
    kost.forEach(function (r) {
      if (!r || typeof r !== 'object') return;
      var n = str(r.namn), x = str(r.text), e = str(r.enhet);
      var b = (typeof r.belopp === 'number' && isFinite(r.belopp)) ? r.belopp : null;
      if (!n && !x && b === null) return;
      if (b !== null) {
        kh += '<li><b>' + txt(n) + '</b><span>' + txt(kr(b) + (e ? ' ' + e : '')) + '</span></li>';
      } else {
        kh += '<li class="oa__fold-villkor"><b>' + txt(n) + '</b>'
            + (x ? ' <span>' + txt(x) + '</span>' : '') + '</li>';
      }
    });
    kh += '</ul>';
    var kFot = str(data.kostnader_fot);
    if (kFot) kh += '<p class="oa__fold-fot">' + txt(kFot) + '</p>';
    $('oaKostnaderKropp').innerHTML = kh;
    visa($('oaKostnader'), true);
  }

  /* ---- 4c · VAD BEHOVER DU GORA FORE INSTALLATIONEN ---------------------
     Agardokument 29 oktober, avsnitt 2, och agarbesked i motet samma dag,
     ordagrant: "den ska vara global. Den ska visas pa alla oavsett vilken
     laddbox det ar, oavsett om de har valt lastbalansering eller inte."
     Texten ar alltsa INTE villkorad av kundens val, och punkten om
     lastbalansering borjar darfor med "Om du har valt", vilket ar agarens
     egen formulering och losningen pa samma sak.

     Dokumentet ger den till laddbox, elcentral och batteri. Service och
     tillagg far ingen: saknas listan star sektionen kvar dold. */
  var forb = Array.isArray(data.forberedelser) ? data.forberedelser : null;
  if (forb && forb.length) {
    var fh = '<ul class="oa__fold-lista oa__fold-lista--punkt">';
    var n = 0;
    forb.forEach(function (rad) {
      var s = str(rad);
      if (!s) return;
      n++;
      fh += '<li><span>' + txt(s) + '</span></li>';
    });
    fh += '</ul>';
    if (n) { $('oaForberedKropp').innerHTML = fh; visa($('oaForbered'), true); }
  }

  /* ---- 5 · VILLKOREN, I EN FOLD LÄNGST NER -----------------------------
     Ägarens ord 25 oktober, GLOBAL NOTERING: länken och "Läs våra
     köpvillkor" ska ligga under en dropdown som heter Villkor längst ner på
     orderbekräftelsen, likt offerten. Formen är offertens egen fold.
     LÄNKEN SKRIVS HÄR, INTE I MARKUPEN. Ett tomt href är inget villkor:
     saknas adressen står sektionen kvar dold, och kunden får ingen trasig
     länk att trycka på. Texten är offertens, ordagrant. */
  var vUrl = str(offert.villkor_url);
  if (vUrl) {
    $('oaVillkorKropp').innerHTML = '<p class="oa__villkor-rad"><a href="' + txt(vUrl)
      + '" target="_blank" rel="noopener">Läs våra köpvillkor</a></p>';
    visa($('oaVillkor'), true);
  }

  /* SEKTIONEN SOM BAR FOLDARNA visas nar minst en fold gor det, och doljs
     annars helt. Till 31 oktober lag foldarna i tre egna sektioner och
     doldes var for sig; nu ar de tre <details> i EN sektion, som forlagan.
     Utan den har raden stod en tom sektion kvar med sin kantlinje och sin
     spalt pa tillaggsmallen, som bara har villkorsfolden. */
  var _folds = $('oaFolds');
  if (_folds) {
    var _nagon = ['oaKostnader', 'oaForbered', 'oaVillkor'].some(function (i) {
      var e = $(i); return e && !e.hidden;
    });
    visa(_folds, _nagon);
  }

  /* Kontraktsfel hör i byggets logg, inte på kundens sida. prov.py läser
     flaggan; kunden ser bara att ett tal uteblev. */
  if (fel.length) {
    root.setAttribute('data-oa-fel', fel.join(' | '));
    if (window.console && console.warn) console.warn('AMPY_ORDER:', fel.join(' | '));
  }
})();
