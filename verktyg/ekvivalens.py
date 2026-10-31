#!/usr/bin/env python3
"""En borttagen kommentar far inte flytta en enda pixel.

    python3 verktyg/ekvivalens.py            # fem mallar x tva bredder
    python3 verktyg/ekvivalens.py --sjalvprov

VARFOR DEN FINNS. bygg.py strippar kommentarerna ur det som publiceras
(agarbeslut 31 oktober: "Kund ska inte se interna kommenterar"). Att en fil
blev 60 % mindre bevisar ingenting om att den ser likadan ut. En kommentar
mellan tva element ar WHITESPACE for layouten, och whitespace mellan inline-
element RENDERAS: tas den bort kan ett mellanslag forsvinna och raden flytta.
Det ar precis den defekten det har provet finns for.

VAD SOM MATS. Varje element inne i .oa far sin rect avrundad till 0,01 px,
plus kortets hojd. Sidan renderas TVA ganger - en gang ostrippad, en gang
strippad - och de tva fingeravtrycken ska vara IDENTISKA.

PARET MASTE RENDERAS LIKA. Bada varianterna skrivs i en egen katalog ETT steg
under reporoten, precis som fall/, sa att sidans href="styles.css" och
href="../fonts/" loses till samma filer i bada fallen. Lag paret i fall/
pekade ../fonts/ pa fall/fonts/ som inte finns: fonterna foll tillbaka pa
systemets och HELA matningen blev en annan - ett prov som mater fel sak lika
hart som det mater ratt.

Chrome kors med EGEN --user-data-dir och dodas med sin EGEN process-grupp.
Doda ALDRIG Chrome med pkill: det stanger anvandarens riktiga webblasare.
"""
import html as _h
import json
import os
import pathlib
import re
import shutil
import signal
import subprocess
import sys
import time

HAR = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HAR))
sys.path.insert(0, str(HAR / "verktyg"))
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]
BREDDER = [375, 1180]

MATT = """
<script>window.addEventListener('load',function(){
  var kort=document.querySelector('.oa__card');
  var kr=kort.getBoundingClientRect();
  var ut={korthojd:+kr.height.toFixed(2), bredd:innerWidth, element:[]};
  document.querySelectorAll('.oa, .oa *').forEach(function(e){
    if(e.tagName==='PATH'||e.tagName==='RECT'||e.tagName==='STOP') return;
    var r=e.getBoundingClientRect();
    ut.element.push([e.tagName.toLowerCase()+'.'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className||''),
      +(r.left-kr.left).toFixed(2), +(r.top-kr.top).toFixed(2),
      +r.width.toFixed(2), +r.height.toFixed(2)]);
  });
  document.title='MATT'+JSON.stringify(ut);
});</script>
"""


def _rendera_par(namn, sidor, bredd, hojd=1600):
    """{mall: fingeravtryck} for en uppsattning (mall, html, css) i EN Chrome."""
    kat = HAR / ("_ekv-%s-%d" % (namn, time.time_ns()))
    kat.mkdir()
    try:
        iframes, ordning = [], []
        for i, (mall, html, css) in enumerate(sidor):
            (kat / "styles.css").write_text(css, encoding="utf-8")
            f = kat / ("s%d.html" % i)
            f.write_text(html.replace("</body>", MATT + "</body>"), encoding="utf-8")
            iframes.append('<iframe id="f%d" src="%s" width="%d" height="%d"></iframe>'
                           % (i, f.name, bredd, hojd))
            ordning.append(mall)
        yttre = kat / "y.html"
        yttre.write_text(
            '<!DOCTYPE html><meta charset="utf-8"><title>vantar</title>'
            '<style>html,body{margin:0}iframe{border:0;display:block}</style><body>'
            + "".join(iframes) +
            '<script>var n=0,N=%d,t=setInterval(function(){n++;var ut=[],klar=0;'
            'for(var i=0;i<N;i++){try{var d=document.getElementById("f"+i).contentDocument;'
            'if(d&&d.title.indexOf("MATT")===0){klar++;ut.push(d.title.slice(4));}'
            'else{ut.push("null");}}catch(e){ut.push("null");}}'
            'if(klar===N){document.title="MATT["+ut.join(",")+"]";clearInterval(t);}'
            'if(n>800)clearInterval(t);},20);</script></body>' % len(sidor),
            encoding="utf-8")
        profil = HAR / ("_cr-%d" % time.time_ns())
        cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--allow-file-access-from-files", "--force-prefers-reduced-motion",
               "--hide-scrollbars", "--user-data-dir=" + str(profil),
               "--virtual-time-budget=25000",
               "--window-size=%d,%d" % (bredd + 80, hojd * len(sidor) + 120),
               "--dump-dom", yttre.as_uri()]
        # ETT FORSOK TILL, EN GANG. Agarens egen Chrome kor samtidigt
        # (uppmatt: 73 processer) och en timeout dar ar INGET SVAR, inte ett
        # matvarde. Ett riktigt hang faller BADA forsoken; en resurskonflikt
        # gor det inte, sa raden doljer inget fel - den skiljer de tva at.
        out = None
        for _forsok in (1, 2):
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                out, _ = p.communicate(timeout=300)
                break
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # BARA min egen grupp
                if _forsok == 2:
                    subprocess.run(["rm", "-rf", str(profil)], check=False)
                    return {}
        subprocess.run(["rm", "-rf", str(profil)], check=False)
        m = re.search(r"<title>MATT(.*?)</title>", out.decode("utf-8", "replace"), re.S)
        if not m:
            return {}
        return {mall: d for mall, d in zip(ordning, json.loads(_h.unescape(m.group(1)))) if d}
    finally:
        shutil.rmtree(kat, ignore_errors=True)


def par(muter_strip=None):
    """[(mall, ostrippad_html, ostrippad_css, strippad_html, strippad_css)].

    muter_strip later sjalvprovet gora STRIPPNINGEN destruktiv. Det ar den
    riktiga risken: en kommentar som tas bort ar layoutneutral i vanlig markup
    (darfor 10 av 10 identisk), men en strippare som ater en byte som INTE ar
    en kommentar flyttar nagot - och det ska det har provet se."""
    import bygg
    import strippa
    css = (HAR / "styles.css").read_text(encoding="utf-8")
    def strip(sok, t):
        s_ = strippa.strip_fil(sok, t)
        return muter_strip(sok, s_) if muter_strip else s_
    ut = []
    for mall in MALLAR:
        k = HAR / "exempel" / (mall + ".json")
        rå = bygg.stada(bygg.rendera(k), mall, k.relative_to(HAR))
        ut.append((mall, rå, css,
                   strip(pathlib.Path("x.html"), rå),
                   strip(pathlib.Path("x.css"), css)))
    return ut


def kor(tyst=False, muter_strip=None):
    """(antal jamforelser, fel)."""
    p = par(muter_strip)
    antal, fel = 0, []
    for bredd in BREDDER:
        a = _rendera_par("a", [(m, h, c) for m, h, c, _, _ in p], bredd)
        b = _rendera_par("b", [(m, hs, cs) for m, _, _, hs, cs in p], bredd)
        if not a or not b:
            fel.append("@%d: INGET SVAR fran Chrome (inte ett fynd, kor om)" % bredd)
            continue
        for mall, _, _, _, _ in p:
            da, db = a.get(mall), b.get(mall)
            if da is None or db is None:
                fel.append("%s @%d: INGET SVAR" % (mall, bredd))
                continue
            antal += 1
            if da == db:
                if not tyst:
                    print("  %-10s @%-5d IDENTISK   korthojd %.2f, %d element"
                          % (mall, bredd, da["korthojd"], len(da["element"])))
                continue
            skilj = []
            if da["korthojd"] != db["korthojd"]:
                skilj.append("korthojd %.2f -> %.2f" % (da["korthojd"], db["korthojd"]))
            if len(da["element"]) != len(db["element"]):
                skilj.append("%d element -> %d" % (len(da["element"]), len(db["element"])))
            else:
                for x, y in zip(da["element"], db["element"]):
                    if x != y:
                        skilj.append("%s %s -> %s" % (x[0], x[1:], y[1:]))
                        if len(skilj) > 2:
                            break
            fel.append("%s @%d: STRIPPNINGEN FLYTTADE NAGOT: %s"
                       % (mall, bredd, " | ".join(skilj[:3])))
            if not tyst:
                print("  %-10s @%-5d SKILJER    %s" % (mall, bredd, skilj[0]))
    return antal, fel


def sjalvprov():
    """Att provet kan falla.

    FORSTA FORSOKET MUTERADE MARKUPEN: ett mellanslag mellan tva inline-
    element byttes mot en kommentar. Det SLAPPTE FORBI, och skalet ar
    lardomen: en kommentar ar inte whitespace, sa bytet tog bort
    mellanslaget i BADA varianterna och de blev likadana. En mutation som
    andrar bada sidorna av en jamforelse bevisar ingenting.

    Nu muteras STRIPPAREN, vilket ar den verkliga risken: en strippare som
    ater en byte som inte ar en kommentar."""
    def tar_en_css_deklaration(sok, t):
        return t.replace("max-width:440px; ", "") if str(sok).endswith(".css") else t

    def tar_ett_element(sok, t):
        if not str(sok).endswith(".html"):
            return t
        i = t.find('<li class="oa__rad')
        j = t.find("</li>", i)
        return t[:i] + t[j + 5:] if i > 0 and j > i else t

    PROV = [("strippern tar en CSS-deklaration (max-width:440px)", tar_en_css_deklaration),
            ("strippern tar ett element (forsta raden)", tar_ett_element)]
    slapp = 0
    for namn, f in PROV:
        n, fel = kor(tyst=True, muter_strip=f)
        if fel:
            print("  ROTT  %-48s %s" % (namn, fel[0][:90]))
        else:
            print("  GRONT %-48s SLAPPTE FORBI (%d jamforelser)" % (namn, n))
            slapp += 1
    print()
    print("%d mutationer, %d slapp forbi" % (len(PROV), slapp))
    return slapp


if __name__ == "__main__":
    if "--sjalvprov" in sys.argv:
        raise SystemExit(1 if sjalvprov() else 0)
    n, fel = kor()
    print()
    print("%d jamforelser (fem mallar x tva bredder)" % n)
    if fel:
        print("\n%d FEL:" % len(fel))
        for f in fel:
            print("  * " + f)
        raise SystemExit(1)
    print("%d av %d IDENTISK: strippningen flyttade inte en pixel" % (n, n))
