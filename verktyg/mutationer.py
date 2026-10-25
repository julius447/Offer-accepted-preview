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
import json, pathlib, shutil, subprocess, sys, tempfile

HAR = pathlib.Path(__file__).resolve().parent.parent
RADEN = "ROT förutsätter att du har avdragsutrymme kvar."

def text(fil, gammal, ny):
    def f():
        p = HAR / fil
        s = p.read_text(encoding="utf-8")
        assert gammal in s, "hittar inte %r i %s" % (gammal[:40], fil)
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
  text("script.js", "var delar = [forsta + '.', andra];",
       "var delar = [forsta + '.', andra, '" + RADEN + "'];"),
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
       '<h2 class="oa__eyebrow">Det här accepterade du</h2><p>14 345 kr</p>'),
  "moderoffertens total"),
 ("svar 56, en rad forsvinner fran en bekraftelse",
  text("fall/laddbox.html", '<li class="oa__rad"><span class="oa__rad-text">RFID-taggar, 5-pack',
       '<li class="oa__rad" data-borttagen><span class="oa__rad-text">BORTA, 5-pack'),
  "ägarsvar 56"),
 ("svar 56, tillagget pekar pa en moder som inte finns",
  js("exempel/tillagg.json", lambda d: d["offert"].update(modertyp="belysning")),
  "modertyp"),
]

sak = tempfile.mkdtemp(prefix="oa-sakerhet-")
trasigt = 0
for namn, (filer, muter), vantat in FALL:
    for i, fil in enumerate(filer):
        shutil.copy2(HAR / fil, pathlib.Path(sak) / ("backup%d" % i))
    try:
        muter()
        r = subprocess.run([sys.executable, "prov.py", "--snabb"], cwd=HAR,
                           capture_output=True, text=True)
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
r = subprocess.run([sys.executable, "prov.py", "--snabb"], cwd=HAR, capture_output=True, text=True)
print("ATERSTALLT: %s" % r.stdout.strip().split("\n")[-1])
sys.exit(1 if trasigt else 0)
