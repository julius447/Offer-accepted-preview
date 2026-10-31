#!/usr/bin/env python3
"""Varje orakel ur agarsvaren 25 oktober, bevisat genom att defekten aterinfors.

    python3 verktyg/mutationer.py

En kommentar ar inget orakel, och ett gront prov pa nagot man aldrig sett
falla ar ingen matning. Filen muteras, `prov.py --snabb` kors, felet skrivs
ut, och filen laggs tillbaka byte for byte. INGENTING RORS I OFFERTREPOT.

Talprovet (agarsvar 60) har sitt eget sjalvprov, for det muterar bada sidor:
    python3 verktyg/talen.py <offertrepot> --sjalvprov

EN MUTATION SOM INTE BLIR ROD AR ETT HAL, INTE EN FORBISEELSE. Tva av de
elva slapp forbi forsta gangen, och den ena var ett akta mathal: svar
48-oraklet last synlig(index), och synlig() tar bort dolda element. I
index.html ar varje fyllbart element dolt, sa kontrollen matte en nastan tom
strang. Meningen inskriven i det dolda oaFin gav exit 0.
"""
import json, os, pathlib, shutil, subprocess, sys, tempfile

HAR = pathlib.Path(__file__).resolve().parent.parent
RADEN = "ROT förutsätter att du har avdragsutrymme kvar."

# SERVICERADENS FORSTA PUNKT, PA ETT STALLE.
# Tva mutationer harunder ankrar pa den. Den 30 oktober fick servicens rader
# arbetet OCH materialet pa samma rad (agarsvar 22, kravspec §4), och raden
# gick fran "Byte av 6 strombrytare" till lydelsen nedan. Ankarna skrevs INTE
# om, sa text() traffade noll och harnessen avbrot - vilket var ratt av den,
# men mutationerna hade inte korts sedan den 29:e. Namnd konstant nu, sa
# nasta lydelsebyte traffar ETT stalle och inte tva.
SERVICE_RAD1 = ("Byte av 6 strömbrytare inklusive brytare och "
                "erforderligt installationsmaterial")

# INGEN BYTEKOD, OCH INGEN GAMMAL BYTEKOD KVAR.
# Tva mutationer som inte andrar filens storlek kan annars kora .pyc fran
# forra varvet: Pythons cache jamfor mtime och storlek, och en mutation som
# byter lika manga tecken mot lika manga ser likadan ut. Provet hade da
# godkant en defekt som aldrig fanns pa disk. Billigare att stanga an att
# felsoka.
MILJO = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")


def rensa_bytekod():
    for d in list(HAR.rglob("__pycache__")):
        shutil.rmtree(d, ignore_errors=True)

def text(fil, gammal, ny, antal=1):
    """Byter EN forekomst, och RAKNAR forst att den finns i det antal som
    vantas. En mutation som inte traffar ar tyst: str.replace mot ett
    hardspatie eller en omskriven rad byter ingenting, provet forblir gront
    och raden laser som ett bevis for att oraklet haller. Det ar samma
    matfel som hela den har filen finns for att stanga."""
    def f():
        p = HAR / fil
        s = p.read_text(encoding="utf-8")
        hittade = s.count(gammal)
        assert hittade == antal, ("mutationen traffar inte: %r star %d ganger i %s, "
                                  "vantade %d" % (gammal[:60], hittade, fil, antal))
        p.write_text(s.replace(gammal, ny, 1), encoding="utf-8")
    return [fil], f

def bada(a, b):
    """Tva filer i samma mutation: kontraktet OCH den byggda sidan."""
    fa, ga = a
    fb, gb = b
    return fa + fb, (lambda: (ga(), gb()))

def js(fil, andra):
    def f():
        p = HAR / fil
        d = json.loads(p.read_text(encoding="utf-8"))
        andra(d)
        p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return [fil], f

FALL = [
 ("svar 48, meningen aterinford i ETT KONTRAKT",
  js("exempel/elcentral.json",
     lambda d: d["order"].update(underrubrik=d["order"]["underrubrik"] + " " + RADEN)),
  "avdragsutrymme"),
 ("svar 48, meningen aterinford i MARKUPEN",
  text("index.html", '<p class="oa__fin" id="oaFin" hidden></p>',
       '<p class="oa__fin" id="oaFin" hidden>' + RADEN + '</p>'),
  "avdragsutrymme"),
 ("svar 48, meningen aterinford i RENDERAREN",
  text("script.js", "return [forsta, forsta + '. Avdragen dras direkt på fakturan.'];",
       "return [forsta, forsta + '. Avdragen dras direkt på fakturan. " + RADEN + "'];"),
  "avdragsutrymme"),
 ("svar 46, datumet hardkodat i markupen",
  text("index.html", '<p class="oa__accept" id="oaAccept" hidden>Accepterad <span id="oaAcceptDatum"></span></p>',
       '<p class="oa__accept" id="oaAccept">Accepterad 27 oktober 2026</p>'),
  "månaden"),
 ("svar 46, ett datum som inte finns i kalendern",
  js("exempel/batteri.json", lambda d: d["offert"].update(accepterad="2026-13-01")),
  "datum i kalendern"),
 ("svar 46, acceptdatumet drar med sig ett giltig till",
  js("exempel/service.json", lambda d: d["offert"].update(giltig_till_lang="27 oktober 2026")),
  "giltighetstid"),
 ("svar 56, sidan bar ett annat nummer an sitt kontrakt",
  js("exempel/service.json", lambda d: d["offert"].update(referens="2026-0641")),
  "Bekräftelsen ska bära sin EGEN"),
 ("svar 56, tva mallar visar samma offertnummer",
  bada(js("exempel/service.json", lambda d: d["offert"].update(referens="2026-0641")),
       text("fall/service.html", "2026-0643", "2026-0641")),
  "unik orderbekräftelse"),
 ("svar 56, moderoffertens total star pa tillaggets bekraftelse",
  text("fall/tillagg.html", '<h2 class="oa__eyebrow">Det här accepterade du</h2>',
       '<h2 class="oa__eyebrow">Det här accepterade du</h2><p>14 620 kr</p>'),
  # TALET FOLJDE MED LADDBOXENS TOTAL 29 OKTOBER: 14 345 -> 14 620, efter att
  # RFID 5-pack gick 175 -> 450 i offertrepot. Mutationen skrev det GAMLA
  # talet, och da kande oraklet inte igen det som moderns total: sviten blev
  # rod av ett annat skal, och harnessen rapporterade MISS i stallet for ROTT.
  # En mutation som bar ett foraldrat tal provar inte det den sager sig prova.
  "moderoffertens total"),
 ("svar 56, en rad forsvinner fran en bekraftelse",
  text("fall/laddbox.html", '<li class="oa__rad"><span class="oa__rad-text">RFID-taggar, 5-pack',
       '<li class="oa__rad" data-borttagen><span class="oa__rad-text">BORTA, 5-pack'),
  "ägarsvar 56"),
 ("svar 56, tillagget pekar pa en moder som inte finns",
  js("exempel/tillagg.json", lambda d: d["offert"].update(modertyp="belysning")),
  "modertyp"),

 # ---- AGARENS GENOMGANG 25 OKTOBER, SEX PUNKTER ----------------------------
 # Varje punkt han gav har minst en mutation. En punkt utan mutation ar en
 # punkt vi bara pastar att vi gjort.

 # 1. BARA RUBRIKERNA OCH PRISET
 ("25 okt 1, pottmarkningen aterinford pa en rad",
  text("fall/laddbox.html", '<span class="oa__rad-text">RFID-taggar, 5-pack</span>',
       '<span class="oa__rad-text">RFID-taggar, 5-pack'
       '<small class="oa__rad-pott">Grön teknik-avdrag</small></span>'),
  "pottmärkning"),
 ("25 okt 1, specen 'i stallet for' bortstadad med markningen",
  text("fall/laddbox.html", "<small>i stället för 5 meter</small>", ""),
  "har tappat"),

 # 2. GRANNRABATTBLOCKET AR EN MENING
 ("25 okt 2, noten under raderna aterinford i markupen",
  text("fall/laddbox.html", '<h3 class="oa__ingar-rubrik"',
       '<p class="oa__not" id="oaNot">Upp till 1 500 kr av, 500 kr för varje granne '
       'som beställer.</p><h3 class="oa__ingar-rubrik"'),
  "noten under raderna"),
 ("25 okt 2, faltet not aterinfort i ett kontrakt",
  js("exempel/laddbox.json",
     lambda d: d["order"]["utestaende"][0].update({"not": "Upp till 1 500 kr av."})),
  "fältet `not`"),

 # 3. VILLKOREN I EN FOLD LANGST NER
 ("25 okt 3, folden heter nagot annat an Villkor",
  text("fall/service.html", '<summary>Villkor<svg class="oa__fold-pil"',
       '<summary>Köpvillkor<svg class="oa__fold-pil"'),
  "heter inte Villkor"),
 ("25 okt 3, kopvillkorslanken star kvar i finstilten ocksa",
  text("fall/batteri.html", "Avdragen dras direkt på fakturan.</p>",
       'Avdragen dras direkt på fakturan. <a href="https://ampy.se/kopvillkor">'
       "Läs våra köpvillkor</a></p>"),
  "står 2 gånger"),
 # ANKARET GJORDES UNIKT 29 OKTOBER. Klassen oa__villkor delas nu av tre
 # sektioner (kostnader, forberedelser, villkor), sa anten traffade tre och
 # harnessen vagrade hellre an muterade fel stalle. Id:t sager vilken fold det
 # ar; klassen sager bara vilken form den har.
 ("25 okt 3, folden ligger inte langst ner",
  text("fall/elcentral.html", '<section class="oa__section oa__villkor" id="oaVillkor"',
       '<section class="oa__section" id="oaVillkor"'),
  "näst sist"),

 # 3b. DE TVA FOLDARNA FRAN 29 OKTOBER
 ("29 okt, stegremsan tillbaka pa en sida",
  text("fall/laddbox.html", '<section class="oa__section oa__villkor" id="oaKostnader"',
       '<section class="oa__section"><ol class="oa__steps"><li class="oa__step">'
       'Din accept ar registrerad</li></ol></section>'
       '<section class="oa__section oa__villkor" id="oaKostnader"'),
  "steglista igen"),
 ("29 okt, foldarna i fel ordning",
  text("fall/batteri.html", '<summary>Kostnader som kan tillkomma',
       '<summary>Vad behöver du göra före installationen?'),
  "foldarna"),
 ("29 okt, kostnadsfolden syns utan innehall i kontraktet",
  text("fall/service.html", '<section class="oa__section oa__villkor" id="oaKostnader" hidden=""',
       '<section class="oa__section oa__villkor" id="oaKostnader"'),
  "oaKostnader"),
 ("29 okt, forberedelsefolden goms trots att kontraktet har texten",
  text("fall/elcentral.html", '<section class="oa__section oa__villkor" id="oaForbered"',
       '<section class="oa__section oa__villkor" id="oaForbered" hidden=""'),
  "oaForbered"),
 ("29 okt, ett kostnadsbelopp driftar fran katalogen",
  text("exempel/laddbox.json", '"belopp": 245,', '"belopp": 240,'),
  "245"),

 # 4. FINSTILTEN UTAN PARENTES
 ("25 okt 4, parentesen tillbaka i finstilten",
  text("fall/batteri.html", "inkl. moms, efter skattereduktion. Avdragen",
       "inkl. moms, efter skattereduktion (Grön teknik). Avdragen"),
  "utgick 25 oktober"),
 ("25 okt 4, kvittonoten sager nagot annat",
  text("fall/service.html",
       '<span class="oa__kvitto-not" id="oaKvittoNot">inkl. moms, efter skattereduktion</span>',
       '<span class="oa__kvitto-not" id="oaKvittoNot">inkl. moms, efter skattereduktion (ROT)</span>'),
  "kvittonoten"),

 # 5. EN MALL, EN SKILLNAD
 ("25 okt 5, en mall far egen markup utanfor stegen",
  text("fall/service.html", '<h2 class="oa__eyebrow">Det här accepterade du</h2>',
       '<h2 class="oa__eyebrow">Det här accepterade du</h2><p class="oa__extra"></p>'),
  "olika markup utanför"),
 # MUTATIONEN "en andra mall byter sin steglista" AR AVVECKLAD 29 OKTOBER,
 # och ersatt i stallet for raderad. Den bevisade att samma-mall sag nar en
 # ANNAN mall an tillagget fick en egen steglista. Agarordern samma dag tog
 # bort remsan fran alla fem, sa det pastaendet finns inte langre att bevisa:
 # ankaret traffade noll och harnessen vagrade, vilket var ratt av den.
 # Samma sanning en vaning upp bevisas nu av "29 okt, stegremsan tillbaka pa
 # en sida" ovanfor: ingen av de fem far HA en steglista. Ett borttaget krav
 # ar en kontroll mindre for alltid; ett vant krav stoppar aterkomsten.

 # 6. ALLT SOM INGAR AR EN REN PUNKTLISTA
 ("25 okt 6, brodtext tillbaka under en punkt",
  text("fall/service.html", "<span>%s</span>" % SERVICE_RAD1,
       "<span>%s<span>hall, vardagsrum och kök</span></span>" % SERVICE_RAD1),
  "brödtext under sig"),
 ("25 okt 6, en ingar-post blir ett objekt igen",
  js("exempel/service.json",
     lambda d: d["order"].update(ingar=[{"text": p, "spec": "x"} if i == 0 else p
                                        for i, p in enumerate(d["order"]["ingar"])])),
  "inte en sträng"),
 ("25 okt 6, en ingar-strang som inte star i offertrepot",
  bada(js("exempel/service.json",
          lambda d: d["order"].update(ingar=[SERVICE_RAD1.replace("6", "7", 1)]
                                            + d["order"]["ingar"][1:])),
       text("fall/service.html", "<span>%s</span>" % SERVICE_RAD1,
            "<span>%s</span>" % SERVICE_RAD1.replace("6", "7", 1))),
  "star inte ordagrant i offertrepot"),

 # ---- PROVEN AGAREN BAD OM ------------------------------------------------
 ("svar 46, provfallet bar nagot mer an datumet",
  js("exempel/prov-acceptdatum.json", lambda d: d["order"].update(etikett="Summa")),
  "mer än offert.accepterad"),
 ("svar 46, ett riktigt fall far ett pahittat acceptdatum",
  js("exempel/laddbox.json", lambda d: d["offert"].update(accepterad="2026-10-25")),
  "förorena"),
 ("svar 46, provfallet skriver ISO-datumet rakt av",
  text("fall/prov-acceptdatum.html",
       '<span id="oaAcceptDatum">25 oktober 2026</span>',
       '<span id="oaAcceptDatum">2026-10-25</span>'),
  "ISO-datumet"),
 ("svar 46, provfallets sida bar nagot mer an acceptraden",
  text("fall/prov-acceptdatum.html", "5 av 5 i betyg på Google",
       "5 av 5 i betyg pa Google"),
  "väntade 2 och bara"),
 ("svar 56, brickan slutar saga att numret ar moderns",
  text("fall/tillagg.html", '<span id="oaRefEtikett">Tillägg till offert</span>',
       '<span id="oaRefEtikett">Offert</span>'),
  "brickans etikett"),
 ("svar 56, moderns paketnamn star pa tillaggets sida",
  text("fall/tillagg.html", '<h2 class="oa__eyebrow">Det här accepterade du</h2>',
       '<h2 class="oa__eyebrow">Det här accepterade du</h2><p>Paket Premium</p>'),
  "order.paket.namn"),

 # ---- OCH SKARMJAMFORELSEN, SOM VAR ROD UTAN ATT NAGON SAG DET ------------
 ("skarmen glider utan en post i AVSIKT",
  text("index.html", '<p class="oa__contact">',
       '<p class="oa__nyhet">En ny rad ingen forklarat</p><p class="oa__contact">'),
  "jamfor-skarm"),
]

sak = tempfile.mkdtemp(prefix="oa-sakerhet-")
trasigt = 0
for namn, (filer, muter), vantat in FALL:
    for i, fil in enumerate(filer):
        shutil.copy2(HAR / fil, pathlib.Path(sak) / ("backup%d" % i))
    try:
        muter()
        rensa_bytekod()
        r = subprocess.run([sys.executable, "-B", "prov.py", "--snabb"], cwd=HAR,
                           capture_output=True, text=True, env=MILJO)
        rader = [x.strip(" *") for x in r.stdout.split("\n") if vantat in x]
        ok = r.returncode != 0 and rader
        print("  %-4s %-54s %s" % ("ROTT" if ok else "MISS", namn,
              (" ".join(rader[0].split())[:120] if rader else
               ("exit=%d, inget fel om %r" % (r.returncode, vantat)))))
        trasigt += 0 if ok else 1
    finally:
        for i, fil in enumerate(filer):
            shutil.copy2(pathlib.Path(sak) / ("backup%d" % i), HAR / fil)
print("\n%d mutationer, %d slapp forbi" % (len(FALL), trasigt))
rensa_bytekod()
r = subprocess.run([sys.executable, "-B", "prov.py", "--snabb"], cwd=HAR,
                   capture_output=True, text=True, env=MILJO)
print("ATERSTALLT: %s" % r.stdout.strip().split("\n")[-1])
sys.exit(1 if trasigt else 0)
