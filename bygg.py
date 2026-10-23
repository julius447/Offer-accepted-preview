#!/usr/bin/env python3
"""Bygger fall/<mall>.html ur index.html och exempel/<mall>.json.

    python3 bygg.py            # alla fem fallen
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

HAR = pathlib.Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
TMP = HAR / ".tmp"
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]


def rendera(kontrakt_fil):
    """index.html + kontraktet, kört i Chrome, DOM:en tillbaka som text."""
    index = (HAR / "index.html").read_text(encoding="utf-8")
    data = json.loads(kontrakt_fil.read_text(encoding="utf-8"))
    nyckel = "<script src=\"script.js\"></script>"
    if index.count(nyckel) != 1:
        raise SystemExit("index.html: hittar inte script-taggen att injicera före")
    injektion = ('<script id="oaKontrakt">window.AMPY_ORDER=%s;</script>\n'
                 % json.dumps(data, ensure_ascii=False))
    sida = index.replace(nyckel, injektion + nyckel)

    TMP.mkdir(exist_ok=True)
    # Provfilen MÅSTE ligga i reporoten. Låg den i .tmp/ pekade sidans egna
    # relativa src="script.js" och href="styles.css" på .tmp/script.js, som
    # inte finns: Chrome laddade alltså varken renderaren eller stilarna och
    # dumpade en sida där ingenting var fyllt, utan ett enda felmeddelande.
    prov = HAR / ("_bygg-%d.html" % time.time_ns())
    prov.write_text(sida, encoding="utf-8")
    profil = TMP / ("cr-%d" % time.time_ns())
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--allow-file-access-from-files", "--force-prefers-reduced-motion",
           "--user-data-dir=" + str(profil), "--virtual-time-budget=6000",
           "--dump-dom", "file://" + str(prov)]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        ut, _ = p.communicate(timeout=90)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # BARA min egen grupp
        raise SystemExit("Chrome svarade inte på 90 sekunder")
    finally:
        prov.unlink(missing_ok=True)
    return ut.decode("utf-8")


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
    # fall/ ligger ett steg ner.
    for gammal, ny in (('href="styles.css"', 'href="../styles.css"'),
                       ('href="fonts/', 'href="../fonts/')):
        if gammal not in dom:
            raise SystemExit("%s: hittar inte %s att peka om" % (mall, gammal))
        dom = dom.replace(gammal, ny)
    huvud = ("<!-- BYGGD FIL, ÄNDRA INTE FÖR HAND.\n"
             "     Källa: index.html + %s, renderad av script.js i headless Chrome\n"
             "     och sparad som statisk markup. Bygg om med: python3 bygg.py %s\n"
             "     Ingen JavaScript, inget kontrakt kvar i sidan: det här är vad\n"
             "     serversidan ska skicka. -->\n" % (kontrakt_fil.as_posix(), mall))
    return dom.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + huvud, 1)


def main(vilka):
    (HAR / "fall").mkdir(exist_ok=True)
    for mall in vilka:
        k = HAR / "exempel" / (mall + ".json")
        if not k.exists():
            raise SystemExit("hittar inte " + str(k))
        ut = HAR / "fall" / (mall + ".html")
        ut.write_text(stada(rendera(k), mall, k.relative_to(HAR)), encoding="utf-8")
        print("%-10s -> %s  (%d rader)" % (mall, ut.relative_to(HAR), len(ut.read_text(encoding='utf-8').splitlines())))
    # Profilerna är skräp efter bygget.
    for d in TMP.glob("cr-*"):
        subprocess.run(["rm", "-rf", str(d)], check=False)


if __name__ == "__main__":
    main(sys.argv[1:] or MALLAR)
