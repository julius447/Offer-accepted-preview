#!/usr/bin/env python3
"""Bygger fall/<mall>.html ur index.html och exempel/<mall>.json.

    python3 bygg.py            # alla fem fallen plus provfallen
    python3 bygg.py laddbox    # ett fall

EN RENDERARE, INTE TVÅ. Sidan fylls av script.js i webbläsaren. Bygget kör
samma fil i headless Chrome och sparar den DOM som blev, utan script-taggar.
Resultatet är alltså exakt det serversidan ska rendera (SSR), och det är
bevisat av att det är samma kod som producerade det. En andra renderare i
Python hade varit en andra sanning som kan glida.

Filerna i fall/ är statiska: ingen JavaScript, ingen fetch, inget kontrakt
kvar i sidan. De fungerar med JavaScript avstängt, för det finns ingen.

Chrome körs med EGEN --user-data-dir och dödas med sin EGEN process-grupp.
Rör aldrig andra Chrome-processer: pkill "Google Chrome" stänger användarens
riktiga webbläsare med alla flikar.
"""
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "verktyg"))
import strippa

HAR = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TMP = HAR / ".tmp"
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]
# PROVFALL, INTE EN SJATTE MALL. Ett fall som bara finns for att visa en
# mekanism, och som darfor inte rakhas med i de fem. Se exempel/<namn>.json
# for vad varje provfall provar och varifran dess provvarde kommer.
PROVFALL = ["prov-acceptdatum"]

# K: KORTETS STANGDA HOJD, MATT AV BYGGET OCH BAKAD IN I SIDAN.
# Varfor den finns: styles.css centrerar kortet med
#   padding-top:max(husets padding, calc((100dvh - var(--oa-kort))/2))
# i stallet for justify-content:center. Centreringen beror da pa vyporten och
# ett FRUSET matt, inte pa kortets aktuella hojd, sa den rakas inte om nar en
# fold vaxer. Uppmatt 31 oktober: med justify-content:center flyttade sig
# kortets topp -30 till -214 px nar en fold oppnades pa en skarm hogre an
# kortet; med den har raden 0,0 px pa fem mallar och sju vyporter, och
# vilopositionen ar oforandrad (varsta avvikelse 0,2 px, subpixelavrundning).
#
# INGET FALLBACK-VARDE. Gar matningen inte igenom VAGRAR bygget, for ett
# fallback ar ett handhallet tal i forkladnad och det ar precis det talet som
# ska bort. prov.py kraver dessutom att det inbakade talet ar lika med ett
# FARSKT matt ur samma funktion, sa K inte kan drifta i tysthet.
#
# REFERENSVYPORTEN. Korthojden beror pa BREDDEN (laddbox: 1174,7 px vid 768,
# 1222,8 vid 1180, 1268,3 vid 375 - uppmatt). Ett enda K kan darfor inte vara
# exakt vid varje bredd. Det ar inte ett problem for SKIFTET, som ar 0,0 for
# vilket konstant K som helst, bara for vilopositionen: och centreringen
# engagerar bara nar vyporten ar hogre an kortet, vilket i praktiken bara
# hander i det breda bandet (1180 till 1440, dar korthojden ror sig 8 px).
# Smalare an sa ar kortet alltid hogre an skarmen och golvet vinner.
REF_BREDD, REF_HOJD = 1180, 1440

MATT_SKRIPT = """<script id="oaMatt">
(function(){
  var oa=document.querySelector('.oa'), k=document.querySelector('.oa__card');
  if(!oa||!k) return;
  /* STANGDA folder. Matet ar kortets VILOHOJD; en oppen fold hade bakat in
     ett K som ar hogre an sidan nagon kund ser. */
  document.querySelectorAll('.oa__fold').forEach(function(f){ f.open=false; });
  function skriv(){
    var h=k.getBoundingClientRect().height;
    if(!isFinite(h)||h<=0) return;      /* ingen siffra ar battre an en falsk */
    oa.style.setProperty('--oa-kort', h.toFixed(1)+'px');
  }
  /* FONTERNA MASTE VARA INNE. Inter ar sjalvhostad, och matt pa
     fallback-metrik blir korthojden ett annat tal an den kunden far. */
  if(document.fonts&&document.fonts.ready){document.fonts.ready.then(skriv);}else{skriv();}
})();
</script>"""


def _chrome(sida, namn="_bygg", katalog=None):
    """EN Chrome-start, EN uppsattning flaggor. Bade bygget och K-grinden i
    prov.py gar genom den har funktionen: matte de pa tva olika satt vore
    grinden brus i stallet for ett prov. --hide-scrollbars ar med for att en
    klassisk rullist tar ~15 px av bredden och darmed ANDRAR korthojden.

    Chrome kors med EGEN --user-data-dir och dodas med sin EGEN process-grupp.
    Ror aldrig andra Chrome-processer: pkill "Google Chrome" stanger
    anvandarens riktiga webblasare med alla flikar."""
    TMP.mkdir(exist_ok=True)
    # Provfilen MÅSTE ligga i reporoten. Låg den i .tmp/ pekade sidans egna
    # relativa src="script.js" och href="styles.css" på .tmp/script.js, som
    # inte finns: Chrome laddade alltså varken renderaren eller stilarna och
    # dumpade en sida där ingenting var fyllt, utan ett enda felmeddelande.
    # KATALOGEN AR INTE EN SMAKSAK. Sidans egna relativa lankar loses mot
    # filens katalog: index.html pekar pa "styles.css" och maste darfor ligga
    # i reporoten, medan en FARDIG fall/-sida pekar pa "../styles.css" och
    # maste ligga i fall/. Uppmatt 31 oktober: en fardig sida kopierad till
    # reporoten loste ../styles.css utanfor repot, laddade ingen CSS, och
    # kortet mattes till 10 073,7 px. Rimlighetsspaerren i las_kort fangade
    # det; utan den hade det talet bakats in som K.
    prov = (katalog or HAR) / ("%s-%d.html" % (namn, time.time_ns()))
    prov.write_text(sida, encoding="utf-8")
    profil = TMP / ("cr-%d" % time.time_ns())
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--allow-file-access-from-files", "--force-prefers-reduced-motion",
           "--hide-scrollbars",
           "--window-size=%d,%d" % (REF_BREDD, REF_HOJD),
           "--user-data-dir=" + str(profil), "--virtual-time-budget=6000",
           "--dump-dom", "file://" + str(prov)]
    for _forsok in (1, 2):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             start_new_session=True)
        try:
            ut, _ = p.communicate(timeout=180)
            break
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)       # BARA min egen grupp
            if _forsok == 2:
                prov.unlink(missing_ok=True)
                subprocess.run(["rm", "-rf", str(profil)], check=False)
                raise SystemExit("Chrome svarade inte pa tva forsok a 180 s. INGET "
                                 "SVAR, inte ett matvarde.")
    prov.unlink(missing_ok=True)
    subprocess.run(["rm", "-rf", str(profil)], check=False)
    return ut.decode("utf-8")


def las_kort(dom, var):
    """K ur en sida, som float. Inget fallback: saknas talet, eller ar det
    orimligt, VAGRAR anroparen."""
    m = re.search(r'<div class="oa"[^>]*style="[^"]*--oa-kort:\s*([\d.]+)px', dom)
    if not m:
        raise SystemExit("%s: korthojden (--oa-kort) star INTE i sidan. Matningen i "
                         "MATT_SKRIPT gick inte igenom, och bygget skriver ingen sida "
                         "med ett gissat varde." % var)
    k = float(m.group(1))
    if not (300.0 < k < 5000.0):
        raise SystemExit("%s: korthojden mattes till %.1f px, vilket inte ar en sida. "
                         "Ett tal som ar fel ar varre an inget tal." % (var, k))
    return k


def mat_kort(sida_html, var="sidan"):
    """Korthojden for en FARDIG sida (fall/<mall>.html). Samma Chrome, samma
    flaggor, samma matskript som bygget: prov.py kan darfor jamfora det
    inbakade talet med ett farskt matt och lita pa skillnaden."""
    if "</body>" not in sida_html:
        raise SystemExit("%s: hittar inte </body> att mata i" % var)
    # Sidans egen inbakade stil tas bort forst, sa matningen inte laser sitt
    # eget svar: ett orakel som matar sig med facit i hand provar ingenting.
    rensad = re.sub(r'(<div class="oa"[^>]*style="[^"]*)--oa-kort:\s*[\d.]+px;?',
                    r"\1", sida_html)
    return las_kort(_chrome(rensad.replace("</body>", MATT_SKRIPT + "</body>"),
                            "_k", HAR / "fall"), var)


def rendera(kontrakt_fil):
    """index.html + kontraktet, kört i Chrome, DOM:en tillbaka som text."""
    index = (HAR / "index.html").read_text(encoding="utf-8")
    data = json.loads(kontrakt_fil.read_text(encoding="utf-8"))
    nyckel = "<script src=\"script.js\"></script>"
    if index.count(nyckel) != 1:
        raise SystemExit("index.html: hittar inte script-taggen att injicera före")
    injektion = ('<script id="oaKontrakt">window.AMPY_ORDER=%s;</script>\n'
                 % json.dumps(data, ensure_ascii=False))
    # MATSKRIPTET LIGGER SIST, efter script.js: det ar en synkron IIFE som
    # renderar vid parsning, sa kortet ar fyllt nar matningen kor.
    sida = index.replace(nyckel, injektion + nyckel).replace(
        "</body>", MATT_SKRIPT + "</body>")
    dom = _chrome(sida)
    dom, n = re.subn(r'<script id="oaMatt">.*?</script>\s*', "", dom, flags=re.S)
    if n != 1:
        raise SystemExit("bygget: matskriptet stod %d ganger i dumpen, vantade 1. "
                         "Utan det bakas ingen korthojd in, och utan korthojd "
                         "centreras sidan inte." % n)
    las_kort(dom, kontrakt_fil.name)      # VAGRAR har om talet saknas
    return dom


def stada(dom, mall, kontrakt_fil):
    """Bort med all JavaScript, rätt relativa sökvägar ur fall/."""
    # Kontraktet och renderaren ska INTE följa med: sidan är färdigrenderad.
    dom, n1 = re.subn(r'<script id="oaKontrakt">.*?</script>\s*', "", dom, flags=re.S)
    dom, n2 = re.subn(r'<script src="script\.js"></script>\s*', "", dom)
    if n1 != 1 or n2 != 1:
        raise SystemExit("%s: fick bort %d kontrakt och %d script-taggar, väntade 1 och 1"
                         % (mall, n1, n2))
    if "<script" in dom:
        raise SystemExit("%s: det står JavaScript kvar i den byggda sidan" % mall)
    # OCH KORTHOJDEN STAR KVAR. Sidan som skrivs till fall/ ar statisk och har
    # ingen JavaScript som kan rakna om den: star inte talet dar faller
    # padding-top tillbaka till initialvardet 0 och sidan tappar sin toppspalt.
    las_kort(dom, mall)
    # BYGGET SKRIVER ALDRIG EN SIDA RENDERAREN FLAGGAT.
    # Sidan STANGER vid ett fel i kontraktet: den visar inget totalbelopp och
    # satter data-oa-fel pa .oa. Men en stangd sida ar fortfarande en sida,
    # och utan den har raden skrevs den till fall/ och ut pa Pages med ett
    # tomt kvitto. Ett omojligt acceptdatum (2026-02-30), en rad i fel pott
    # eller en total som inte gar ihop ska stoppa BYGGET, inte bara tala om
    # det i en logg kunden aldrig laser. prov.py provar renderingen direkt
    # via rendera() och ror alltsa inte den har sparren.
    flagga = re.search(r'data-oa-fel="([^"]*)"', dom)
    if flagga:
        raise SystemExit("%s: renderaren flaggade kontraktsfel och sidan skrevs INTE: %s"
                         % (mall, flagga.group(1)))
    # fall/ ligger ett steg ner. STILEN PEKAS INTE OM sedan 31 oktober: den
    # publiceras som en STRIPPAD kopia i fall/ bredvid sidan, sa allt en kund
    # laddar fran en bekraftelse ar strippat. Kallan styles.css i reporoten
    # behaller sina kommentarer och ar den utvecklaren laser.
    if 'href="styles.css"' not in dom:
        raise SystemExit("%s: hittar inte stilmallens href" % mall)
    for gammal, ny in (('href="fonts/', 'href="../fonts/'),):
        if gammal not in dom:
            raise SystemExit("%s: hittar inte %s att peka om" % (mall, gammal))
        dom = dom.replace(gammal, ny)
    huvud = ("<!-- BYGGD FIL, ÄNDRA INTE FÖR HAND.\n"
             "     Källa: index.html + %s, renderad av script.js i headless Chrome\n"
             "     och sparad som statisk markup. Bygg om med: python3 bygg.py %s\n"
             "     Ingen JavaScript, inget kontrakt kvar i sidan: det här är vad\n"
             "     serversidan ska skicka. -->\n" % (kontrakt_fil.as_posix(), mall))
    return dom.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + huvud, 1)


# ----------------------------------------------------------- EN VAG UT
# AGARBESLUT 31 OKTOBER, ORDAGRANT: "Kund ska inte se interna kommenterar."
# Uppmatt pa det kunden laddar: 48 % av byten var kommentar, med citerade
# agarbeslut, namngivna personer och vara egna defektdiskussioner i klartext.
#
# TRE KRAV, samma som i offertrepot:
#  1. KALLAN RORS INTE. index.html, styles.css och script.js behaller varje
#     kommentar - de ar det utvecklaren laser, och projektets dyrast byggda
#     tillgang. Bara det BYGGDA stripas.
#  2. EN VAG UT. Varje fil som publiceras skrivs genom lagg_ut(), ocksa
#     kopior. I offertrepot missade sex handkopplade skrivstallen
#     shutil.copy-slingan, och tio filer gick ut med kommentarerna kvar.
#  3. EN GRIND SOM VAGRAR. grind() ar backstoppet: ett missat skrivstalle blir
#     OSHIPPBART i stallet for tyst.
def grind(mal, text):
    """VAGRAR skriva en publicerad fil som fortfarande bar en kommentar.

    TVA OBEROENDE PROV, for att ett prov dar strippern domer sitt eget arbete
    bara sager att den ar konsekvent:
      a) FIXPUNKT: en ny strippning tar inte bort en enda byte till.
      b) BOKSTAVLIG SOKNING efter sekvenser som inte kan sta nagon
         annanstans i DE HAR filerna - '<!--' i html, '/*' i css. Finns de i
         en strang (CSS content:"/*") vagrar grinden anda, och det ar med
         flit: da ska en manniska titta, inte en regel gissa.
    """
    namn, fynd = str(mal), []
    om = strippa.strip_fil(mal, text)
    if om != text:
        fynd.append("strippern tar bort %d byte till: inte en fixpunkt"
                    % (len(text.encode()) - len(om.encode())))
    if namn.endswith(".html") and "<!--" in text:
        fynd.append("'<!--' star kvar i markupen")
    if namn.endswith(".css") and "/*" in text:
        fynd.append("'/*' star kvar i stilen")
    if fynd:
        raise SystemExit("PUBLICERAS INTE: %s bar en kommentar. %s\n"
                         "Agarbeslut 31 oktober: kund ska inte se interna kommentarer."
                         % (pathlib.Path(namn).name, " | ".join(fynd)))


def lagg_ut(mal, text):
    """ENDA STALLET DAR EN PUBLICERAD FIL SKRIVS. Strippar, grindar, skriver."""
    s = strippa.strip_fil(mal, text)
    grind(mal, s)
    mal.write_text(s, encoding="utf-8")
    return s


def main(vilka):
    (HAR / "fall").mkdir(exist_ok=True)
    for mall in vilka:
        k = HAR / "exempel" / (mall + ".json")
        if not k.exists():
            raise SystemExit("hittar inte " + str(k))
        ut = HAR / "fall" / (mall + ".html")
        lagg_ut(ut, stada(rendera(k), mall, k.relative_to(HAR)))
        print("%-10s -> %s  (%d rader)" % (mall, ut.relative_to(HAR), len(ut.read_text(encoding='utf-8').splitlines())))
    # OVERSIKTEN, OCKSA GENOM EN VAG UT. Kallan ar fall-index.html i
    # reporoten och behaller sina kommentarer; fall/index.html genereras.
    # GRINDEN FANGADE DEN PA FORSTA KORNINGEN: filen var handskriven DIREKT i
    # fall/, bar 514 byte kommentar och gick aldrig genom lagg_ut. Att
    # undanta den hade varit att avveckla grinden pa den enda fil den tog.
    _ovr = HAR / "fall-index.html"
    if not _ovr.exists():
        raise SystemExit("hittar inte fall-index.html, kallan till fall/index.html")
    _o = _ovr.read_text(encoding="utf-8")
    if '"../styles.css"' not in _o:
        raise SystemExit("fall-index.html: hittar inte stilmallens href att peka om")
    lagg_ut(HAR / "fall" / "index.html", _o.replace('"../styles.css"', '"styles.css"'))
    print("%-10s -> fall/index.html  (ur fall-index.html)" % "oversikt")

    # STILEN, STRIPPAD, BREDVID SIDORNA. Fontsokvagarna ar relativa mot
    # CSS-filen, sa de maste peka ett steg upp nar filen ligger i fall/.
    _css = (HAR / "styles.css").read_text(encoding="utf-8")
    if _css.count("url(fonts/") != 2:
        raise SystemExit("styles.css: vantade 2 url(fonts/, hittade %d. Pekas de om "
                         "fel laddar sidan ingen font och ingen sager till."
                         % _css.count("url(fonts/"))
    lagg_ut(HAR / "fall" / "styles.css", _css.replace("url(fonts/", "url(../fonts/"))
    print("%-10s -> fall/styles.css  (strippad kopia)" % "styles")

    # Profilerna är skräp efter bygget.
    for d in TMP.glob("cr-*"):
        subprocess.run(["rm", "-rf", str(d)], check=False)


if __name__ == "__main__":
    main(sys.argv[1:] or (MALLAR + PROVFALL))
