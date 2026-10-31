#!/usr/bin/env python3
"""Radernas geometri: star namnen och prisen pa SAMMA x i hela listan?

    python3 verktyg/radgeometri.py fall/laddbox.html 430
    python3 verktyg/radgeometri.py --alla          # fem mallar x tre bredder

AGARENS FORLAGA ar acceptskarmen. Den centrerar raderna som en GRUPP: namn
och pris intill varandra, gruppen mitt i kortet. Uppmatt pa live 31 oktober
vid 430 px, x fran kortets kanter: forlagan v 132 / h 132, bekraftelsen
v 25 / h 25 - alltsa spande bekraftelsens rader hela kortet, sa namnet
pressades mot vansterkanten och priset mot hogerkanten.

DET SOM AVGOR SAKEN ar inte intrycket utan tre tal:
  1. namnets VANSTERKANT ska vara samma x for varje rad i listan.
  2. prisets HOGERKANT ska vara samma x for varje rad i listan.
  3. listans block ska vara centrerat i kortet, alltsa lika mycket luft pa
     bada sidor - det ar det som gor den till en kvittolista och inte en
     tabell over hela ytan.
Och en fjarde, som ar skalet att 1 och 2 maste matas separat: .oa__head
satter text-align:center och det arvs in i radens textblock. En kort text
far ett smalt block och ser vansterstalld ut, en lang far ett brett och ser
INDRAGEN ut. Tre rader kan alltsa ha tre olika intryck med samma CSS.

Chrome klammer fonsterbredden till 500 px pa macOS, sa den smala bredden
maste komma ur en iframe i ett bredare fonster - samma knep som matt.py.

Chrome kors med EGEN --user-data-dir och dodas med sin EGEN process-grupp.
Doda ALDRIG Chrome med pkill: det stanger anvandarens riktiga webblasare.
"""
import html as _h
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time

HAR = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
MALLAR = ["laddbox", "elcentral", "batteri", "service", "tillagg"]
BREDDER = [375, 430, 1180]
TOL = 0.6          # subpixel; en halv px ar avrundning, en hel ar en defekt

MATT = """
<script>window.addEventListener('load',function(){
  var kort=document.querySelector('.oa__card');
  var lista=document.getElementById('oaRader');
  var kr=kort.getBoundingClientRect();
  var ut={bredd:innerWidth, kort:[+kr.left.toFixed(2),+kr.right.toFixed(2)], rader:[]};
  if(lista){
    var lr=lista.getBoundingClientRect();
    ut.lista={ v:+(lr.left-kr.left).toFixed(2), h:+(kr.right-lr.right).toFixed(2),
               bredd:+lr.width.toFixed(2) };
    [].slice.call(lista.querySelectorAll('.oa__rad')).forEach(function(li){
      var t=li.querySelector('.oa__rad-text'), p=li.querySelector('.oa__rad-pris');
      if(!t||!p) return;
      var tr=t.getBoundingClientRect(), pr=p.getBoundingClientRect();
      /* GLYFKANTEN, INTE BOXKANTEN. Spanens boxar linjerar redan; det ar
         TEXTEN inne i dem som vandrar, for .oa__head:s text-align:center
         arvs in. En Range runt forsta textnoden ger det kunden faktiskt
         ser. Forsta versionen matte bara boxarna och rapporterade noll
         spridning om precis den defekt provet skrevs for. */
      function glyf(el){
        var n=el.firstChild;
        while(n && n.nodeType!==3) n=n.firstChild;
        if(!n) return null;
        var r=document.createRange(); r.selectNodeContents(n);
        var b=r.getBoundingClientRect(); r.detach&&r.detach();
        return b.width?b:null;
      }
      var tg=glyf(t), pg=glyf(p);
      ut.rader.push({
        text:(t.textContent||'').trim().slice(0,30),
        namnV:+(tr.left-kr.left).toFixed(2),      /* namnboxens vansterkant */
        prisH:+(kr.right-pr.right).toFixed(2),    /* prisboxens hogerkant   */
        glyfV: tg?+(tg.left-kr.left).toFixed(2):null,   /* TEXTENS vansterkant */
        glyfH: pg?+(kr.right-pg.right).toFixed(2):null, /* PRISETS hogerkant   */
        justera:getComputedStyle(t).textAlign
      });
    });
  }
  document.title='MATT'+JSON.stringify(ut);
});</script>
"""


def mat_flera(sidor, bredd, hojd=1400):
    """{mall: matvarden} for FLERA sidor i EN Chrome-start.

    EN CHROME PER BREDD, inte en per sida och bredd. Fem mallar x tre
    bredder var 15 starter, och den fulla prov.py startade da 23 Chrome
    totalt: korningen TIMEOUTADE pa 180 sekunder. En hangning ar inget svar
    och inte ett matvarde, men ett prov som inte gar att kora ar inte ett
    prov. Nu ar det tre starter.
    """
    TMP = HAR / ".tmp"
    TMP.mkdir(exist_ok=True)
    stamp = time.time_ns()
    inre, iframes = [], []
    for i, (mall, sida) in enumerate(sidor):
        sida = pathlib.Path(sida).resolve()
        f = sida.parent / ("_rg%d-%d.html" % (i, stamp))
        f.write_text(sida.read_text(encoding="utf-8").replace("</body>", MATT + "</body>"),
                     encoding="utf-8")
        inre.append((mall, f))
        iframes.append('<iframe id="f%d" src="%s" width="%d" height="%d"></iframe>'
                       % (i, f.name, bredd, hojd))
    yttre = inre[0][1].parent / ("_rgy-%d.html" % stamp)
    yttre.write_text(
        '<!DOCTYPE html><meta charset="utf-8"><title>vantar</title>'
        '<style>html,body{margin:0}iframe{border:0;display:block}</style><body>'
        + "".join(iframes) +
        '<script>var n=0,N=%d,t=setInterval(function(){n++;var ut=[],klar=0;'
        'for(var i=0;i<N;i++){try{var d=document.getElementById("f"+i).contentDocument;'
        'if(d&&d.title.indexOf("MATT")===0){klar++;ut.push(d.title.slice(4));}'
        'else{ut.push("null");}}catch(e){ut.push("null");}}'
        'if(klar===N){document.title="MATT["+ut.join(",")+"]";clearInterval(t);}'
        'if(n>600)clearInterval(t);},20);</script></body>' % len(inre),
        encoding="utf-8")
    profil = HAR / ("_cr-%d" % stamp)
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--allow-file-access-from-files", "--force-prefers-reduced-motion",
           "--hide-scrollbars", "--user-data-dir=" + str(profil),
           "--virtual-time-budget=20000",
           "--window-size=%d,%d" % (bredd + 80, hojd * len(inre) + 120),
           "--dump-dom", yttre.as_uri()]
    # ETT FORSOK TILL, EN GANG. Agarens egen Chrome kor samtidigt (uppmatt:
    # 73 processer) och en timeout dar ar INGET SVAR, inte ett matvarde. Ett
    # riktigt hang faller BADA forsoken; en resurskonflikt gor det inte, sa
    # raden doljer inget fel - den skiljer de tva at. UPPMATT 31 oktober:
    # samma mutation rapporterade MISS pa en timeout i tre harnesskorningar
    # medan den enskilt blev ROD pa forsta forsoket.
    out = None
    try:
        for _forsok in (1, 2):
            pr = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, start_new_session=True)
            try:
                out, _ = pr.communicate(timeout=240)
                break
            except subprocess.TimeoutExpired:
                os.killpg(os.getpgid(pr.pid), signal.SIGKILL)  # BARA min egen grupp
                if _forsok == 2:
                    return {}
    finally:
        for _, f in inre:
            f.unlink(missing_ok=True)
        yttre.unlink(missing_ok=True)
        subprocess.run(["rm", "-rf", str(profil)], check=False)
    m = re.search(r"<title>MATT(.*?)</title>", out.decode("utf-8", "replace"), re.S)
    if not m:
        return {}
    lista = json.loads(_h.unescape(m.group(1)))
    return {mall: d for (mall, _), d in zip(inre, lista) if d}


def mat(sida, bredd, hojd=1400):
    d = mat_flera([("en", sida)], bredd, hojd)
    return d.get("en")


def doma(d):
    """(fel, sammanfattning) for EN matning."""
    fel = []
    if not d.get("rader"):
        return fel, "inga rader"
    # GLYFKANTEN ar det som domer. Boxkanten star kvar i utskriften for att
    # skillnaden mellan de tva ar hela fyndet.
    nv = [r["glyfV"] for r in d["rader"] if r.get("glyfV") is not None] \
         or [r["namnV"] for r in d["rader"]]
    ph = [r["glyfH"] for r in d["rader"] if r.get("glyfH") is not None] \
         or [r["prisH"] for r in d["rader"]]
    sprid_n, sprid_p = max(nv) - min(nv), max(ph) - min(ph)
    if sprid_n > TOL:
        varst = max(d["rader"], key=lambda r: abs((r.get("glyfV") or r["namnV"]) - min(nv)))
        fel.append("namnens TEXT sprider %.2f px i vansterkant (%r star pa %.2f, "
                   "minsta %.2f). Boxarna linjerar; glyferna gor det inte."
                   % (sprid_n, varst["text"], varst.get("glyfV"), min(nv)))
    if sprid_p > TOL:
        varst = max(d["rader"], key=lambda r: abs((r.get("glyfH") or r["prisH"]) - min(ph)))
        fel.append("prisens TEXT sprider %.2f px i hogerkant (%r star pa %.2f, "
                   "minsta %.2f)" % (sprid_p, varst["text"], varst.get("glyfH"), min(ph)))
    l = d.get("lista")
    if l and abs(l["v"] - l["h"]) > TOL:
        fel.append("listan ar inte centrerad: v %.2f mot h %.2f" % (l["v"], l["h"]))
    jus = {r["justera"] for r in d["rader"]}
    if jus - {"left", "start"}:
        fel.append("radtexten ar %s, inte vansterstalld - .oa__head:s text-align:center "
                   "arvs in och ger korta och langa texter olika intryck" % sorted(jus))
    return fel, ("lista v %.2f h %.2f bredd %.2f | namnV %s | prisH %s"
                 % (l["v"], l["h"], l["bredd"],
                    "=%.2f" % nv[0] if sprid_n <= TOL else "spridning %.2f" % sprid_n,
                    "=%.2f" % ph[0] if sprid_p <= TOL else "spridning %.2f" % sprid_p))


def kor(tyst=False):
    antal, fel = 0, []
    sidor = []
    for mall in MALLAR:
        f = HAR / "fall" / (mall + ".html")
        if f.exists():
            sidor.append((mall, f))
        else:
            fel.append("%s: fall/%s.html saknas" % (mall, mall))
    for b in BREDDER:
        matt = mat_flera(sidor, b)
        if not matt:
            fel.append("@%d: INGET SVAR fran Chrome (inte ett fynd, kor om)" % b)
            continue
        for mall, _ in sidor:
            d = matt.get(mall)
            if d is None:
                fel.append("%s @%d: INGET SVAR (inte ett fynd)" % (mall, b))
                continue
            antal += 1
            f_, sam = doma(d)
            for x in f_:
                fel.append("%s @%d: %s" % (mall, b, x))
            if not tyst:
                print("  %-10s @%-5d %s" % (mall, b, sam))
    return antal, fel


if __name__ == "__main__":
    if "--alla" in sys.argv or len(sys.argv) < 3:
        n, fel = kor()
        print()
        print("%d matningar (fem mallar x tre bredder)" % n)
        if fel:
            print("\n%d FEL:" % len(fel))
            for x in fel:
                print("  * " + x)
            raise SystemExit(1)
        print("alla gröna: namnen och prisen linjerar, listan ar centrerad")
    else:
        d = mat(sys.argv[1], int(sys.argv[2]))
        print(json.dumps(d, ensure_ascii=False, indent=1))
