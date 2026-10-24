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
  var POTT = {
    'gron-teknik': { etikett: 'Grön teknik-avdrag' },
    'rot':         { etikett: 'ROT-avdrag' },
    'inget':       { etikett: 'Utan avdrag' }
  };

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

     DEN HÄR SIDAN ÄR SAMMA FALL SOM DEN DELADE ACCEPTSKÄRMEN: en yta för fem
     mallar. Där löstes det med fast text "inkl. moms, efter skattereduktion",
     eftersom ett delat block inte kan namnge en pott som bara gäller på en av
     fem sidor. Här BÄR kontraktet potterna, så parentesen kan säga vilka två
     det faktiskt är. Samma ord, fylld parentes. */
  function pottrad(potter) {
    var gt = potter.indexOf('gron-teknik') >= 0, rot = potter.indexOf('rot') >= 0;
    var namn = [];
    if (gt) namn.push('Grön teknik');
    if (rot) namn.push('ROT');
    var forsta, andra;
    if (namn.length) {
      forsta = 'inkl. moms, efter skattereduktion (' + namn.join(' och ') + ')';
      andra = (namn.length > 1 ? 'Avdragen' : 'Avdraget') + ' dras direkt på fakturan.';
    } else {
      forsta = 'inkl. moms'; andra = '';
    }
    var delar = [forsta + '.', andra];
    if (potter.indexOf('inget') >= 0 && namn.length) delar.push('Rader utan avdrag är märkta.');
    return [forsta, delar.filter(function (d) { return d; }).join(' ')];
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
     fyller data-oa="offert.referens" och data-oa="bokare.namn" med det i dag.
     Bär sidan ett kontrakt härleds de platta nycklarna ur det, så de två
     vägarna inte kan säga olika. */
  if (data && typeof data === 'object') {
    var o = data.offert || {}, b = data.bokare || {};
    platt = platt || {};
    if (platt['offert.referens'] == null && str(o.referens)) platt['offert.referens'] = str(o.referens);
    if (platt['offert.giltig_till_lang'] == null && str(o.giltig_till_lang)) platt['offert.giltig_till_lang'] = str(o.giltig_till_lang);
    if (platt['bokare.namn'] == null && str(b.fornamn)) platt['bokare.namn'] = str(b.fornamn);
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
  var bokare = data.bokare || {};

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

  /* ---- 2 · STEGEN -------------------------------------------------------
     "ringer och bokar tid" är fel på ett tillägg där elektrikern redan står
     hos kunden. Texterna kommer därför ur kontraktet, inte ur sidan. Saknas
     de står markupens egna, som är den godkända copyn. Namnet sätts bara in
     om det finns: [Bokare] i hakparenteser får aldrig nå en kund, och ett
     namn vi inte har är ingen mening värd att skriva. */
  var fornamn = str(bokare.fornamn);
  if (fornamn) {
    var s2 = root.querySelector('[data-oa-steg="2"]');
    if (s2 && s2.textContent.indexOf('Vi ringer') === 0) {
      s2.textContent = fornamn + ' ringer och bokar tid';
    }
  }
  var steg = Array.isArray(data.steg) ? data.steg : [];
  steg.forEach(function (st, i) {
    if (!st || typeof st !== 'object') return;
    var nr = String(i + 1);
    var rub = root.querySelector('[data-oa-steg="' + nr + '"]');
    var und = root.querySelector('[data-oa-steg-under="' + nr + '"]');
    if (st.ta_bort === true) {
      var li = rub && rub.closest('.oa__step');
      if (li && li.parentNode) li.parentNode.removeChild(li);
      return;
    }
    if (rub && str(st.rubrik)) rub.textContent = str(st.rubrik);
    if (und) {
      if (str(st.under)) und.textContent = str(st.under);
      else if (st.under === null) und.remove();
    }
  });
  /* Tas ett steg bort ska de som står kvar vara numrerade i ordning. Annars
     läser kunden steg 1 och steg 3. */
  var kvar = root.querySelectorAll('#oaSteps .oa__step');
  Array.prototype.forEach.call(kvar, function (li, i) {
    var sif = li.querySelector('.oa__node span');
    if (sif && i > 0) sif.textContent = String(i + 1);
  });

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

  var fel = [];
  if (!netto) fel.push('priser_ar är inte "netto"');

  /* Potterna HÄRLEDS ur raderna, de står inte i kontraktet. Ett fält som kan
     motsäga raderna är ett fält som kommer att motsäga raderna. Bara rader
     med ett belopp räknas: en intresseanmälan dras inte, så den sätter ingen
     pott och ska inte få finstilten att nämna en. */
  var potter = [];
  function pott(v, harBelopp) {
    var p = str(v);
    if (!p || !POTT[p]) { fel.push('okänd avdragspott ' + JSON.stringify(v)); return null; }
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

  /* Blandade potter: varje rad märks. En pott: ingen rad märks, för då är
     märkningen brus. Samma regel som tilläggsmallens orakel,
     offerter/tillagg/offert.py rad 287 till 292. */
  var visaPott = potter.length > 1;

  var html = poster.map(function (p) {
    var pm = (visaPott && p.pott && p.belopp != null)
      ? '<small class="oa__rad-pott">' + txt(POTT[p.pott].etikett) + '</small>' : '';
    var un = p.under ? '<small>' + txt(p.under) + '</small>' : '';
    var pris = (netto && p.belopp != null)
      ? '<span class="oa__rad-pris kr">' + txt(kr(p.belopp)) + '</span>'
      : (p.ord ? '<span class="oa__rad-pris oa__rad-pris--ord">' + txt(p.ord) + '</span>' : '');
    return '<li class="oa__rad' + (p.huvud ? ' oa__rad--huvud' : '') + '">'
         + '<span class="oa__rad-text">' + txt(p.namn) + un + pm + '</span>' + pris + '</li>';
  });

  /* Utestående: ett löfte offerten gav och som bekräftelsen ska kvittera.
     Grannrabatten är det enda fallet i dag. Texten kommer ur den mall som
     gav löftet, ordagrant, och sidan skriver inget eget om den. */
  var noter = [];
  utest.forEach(function (u) {
    if (!u || !str(u.text)) return;
    html.push('<li class="oa__rad"><span class="oa__rad-text">' + txt(str(u.text)) + '</span>'
            + (str(u.ord) ? '<span class="oa__rad-pris oa__rad-pris--ord">' + txt(str(u.ord)) + '</span>' : '')
            + '</li>');
    if (str(u.not)) noter.push(str(u.not));
  });

  $('oaRader').innerHTML = html.join('');
  if (noter.length) { $('oaNot').textContent = noter.join(' '); visa($('oaNot'), true); }

  /* Produktraden. Service och tillägg har ingen produkt och ingen bild: då
     står raden inte där, den står inte tom. */
  var rubrik = str(order.rubrik), under2 = str(order.underrubrik);
  if (rubrik) {
    $('oaProdRubrik').textContent = rubrik;
    if (under2) $('oaProdUnder').textContent = under2; else $('oaProdUnder').remove();
    visa($('oaProd'), true);
  }

  /* "Allt som ingår." Serviceofferten är den mall som inte konfigurerar
     något: kunden läser en lista och svarar ja eller nej. Då är listan hela
     ordern och måste följa med på kvittensen. */
  if (ingar.length) {
    $('oaIngar').innerHTML = ingar.map(function (i) {
      var t = (typeof i === 'string') ? { text: i } : (i || {});
      if (!str(t.text)) return '';
      return '<li>' + BOCK + '<span>' + txt(str(t.text))
           + (str(t.spec) ? '<span>' + txt(str(t.spec)) + '</span>' : '') + '</span></li>';
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

  /* Finstilten. Villkoret står EN gång, här, och inte en gång per rad:
     hedging-direktivet 2026-08-15. Köpvillkorslänken sätts bara om adressen
     finns: ett tomt href är inget villkor. */
  var fin = [];
  if (netto && (poster.length || total != null)) fin.push(kort[1]);
  var vUrl = str(offert.villkor_url);
  if (fin.length || vUrl) {
    var h = fin.map(txt).join(' ');
    if (vUrl) h += (h ? ' ' : '')
      + '<a href="' + txt(vUrl) + '" target="_blank" rel="noopener">Läs våra köpvillkor</a>';
    $('oaFin').innerHTML = h;
    visa($('oaFin'), true);
  }

  visa($('oaOrder'), !!(poster.length || ingar.length || rubrik));

  /* Kontraktsfel hör i byggets logg, inte på kundens sida. prov.py läser
     flaggan; kunden ser bara att ett tal uteblev. */
  if (fel.length) {
    root.setAttribute('data-oa-fel', fel.join(' | '));
    if (window.console && console.warn) console.warn('AMPY_ORDER:', fel.join(' | '));
  }
})();
