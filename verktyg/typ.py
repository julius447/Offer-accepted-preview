#!/usr/bin/env python3
"""Räknar typstorlekarna och radhöjderna på en byggd sida.

    python3 verktyg/typ.py fall/laddbox.html 390
    python3 verktyg/typ.py fall/laddbox.html 390 --element

Huset har SJU storlekar: 30 / 24 / 20 / 17 / 15 / 13 / 11. Ett värde utanför
skalan är en bugg, inte en smaksak (gemensamt/FALLOR.md, "Rytm och luft").

MÄTNINGEN LÄSER DEN RENDERADE STORLEKEN, inte den som står i CSS. En clamp,
en ärvd procent eller ett `!important` i en mediafråga syns inte i källan men
syns här. Uppmätt 2026-10-24 före skalpasset: ELVA storlekar vid 390 px
(27, 19, 17, 16, 15, 14.5, 14, 13, 12.5, 12, 11).

Och den läser bara element som bär EGEN text: ett `div` som ärver 15 px och
inte har någon egen textnod räknas inte, annars räknas samma storlek en gång
per nivå i trädet och skalan ser bredare ut än den är.

Chrome klämmer fönsterbredden till ~500 px på macOS, så den smala bredden
kommer ur en iframe i ett bredare fönster. Egen --user-data-dir, egen
process-grupp, aldrig pkill: det stänger användarens riktiga webbläsare.
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

SKALA = (30, 24, 20, 17, 15, 13, 11)

SOND = """
<script>window.addEventListener('load',function(){
  var ut={storlekar:{}, element:[]};
  function egenText(e){
    for (var i=0;i<e.childNodes.length;i++){
      var n=e.childNodes[i];
      if(n.nodeType===3 && n.nodeValue.trim()) return true;
    }
    return false;
  }
  document.querySelectorAll('.oa, .oa *').forEach(function(e){
    if(e.closest('svg')) return;
    if(!egenText(e)) return;
    var st=getComputedStyle(e);
    if(st.display==='none'||e.hidden) return;
    var px=Math.round(parseFloat(st.fontSize)*100)/100;
    var lh=st.lineHeight==='normal'?'normal':Math.round(parseFloat(st.lineHeight)*100)/100;
    ut.storlekar[px]=(ut.storlekar[px]||0)+1;
    ut.element.push({k:(e.className&&e.className.baseVal===undefined?e.className:e.tagName)||e.tagName,
                     px:px, lh:lh, w:st.fontWeight,
                     t:(e.textContent||'').trim().slice(0,30)});
  });
  document.title='MATT'+JSON.stringify(ut);
});</script>
"""


def matt(sida, bredd):
    """{storlekar: {px: antal}, element: [...]} för sidan vid den bredden."""
    sida = pathlib.Path(sida).resolve()
    inner = sida.parent / ("_typ-%d.html" % time.time_ns())
    inner.write_text(sida.read_text(encoding="utf-8").replace("</body>", SOND + "</body>"),
                     encoding="utf-8")
    yttre = sida.parent / ("_typy-%d.html" % time.time_ns())
    yttre.write_text(
        '<!DOCTYPE html><meta charset="utf-8"><title>vantar</title>'
        '<style>html,body{margin:0}iframe{border:0;display:block}</style>'
        '<body><iframe id="f" src="%s" width="%d" height="2600"></iframe><script>'
        'var n=0,t=setInterval(function(){n++;try{var d=document.getElementById("f").contentDocument;'
        'if(d&&d.title.indexOf("MATT")===0){document.title=d.title;clearInterval(t);}}catch(e){}'
        'if(n>400)clearInterval(t);},20);</script></body>' % (inner.name, bredd),
        encoding="utf-8")

    profil = HAR / ("_cr-%d" % time.time_ns())
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
           "--allow-file-access-from-files", "--force-prefers-reduced-motion", "--hide-scrollbars",
           "--user-data-dir=" + str(profil), "--virtual-time-budget=12000",
           "--window-size=%d,1200" % (bredd + 80), "--dump-dom", yttre.as_uri()]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        out, _ = p.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)   # BARA min egen grupp
        raise SystemExit("Chrome svarade inte")
    finally:
        inner.unlink(missing_ok=True)
        yttre.unlink(missing_ok=True)
        subprocess.run(["rm", "-rf", str(profil)], check=False)
    m = re.search(r"<title>MATT(.*?)</title>", out.decode("utf-8", "replace"), re.S)
    if not m:
        raise SystemExit("%s: inga matvarden tillbaka" % sida.name)
    return json.loads(_h.unescape(m.group(1)))


def utanfor_skalan(d):
    """[(px, antal)] för varje storlek som inte är en av husets sju."""
    ut = []
    for px, antal in d["storlekar"].items():
        v = float(px)
        if v != round(v) or round(v) not in SKALA:
            ut.append((v, antal))
    return sorted(ut, reverse=True)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    sida, bredd = pathlib.Path(sys.argv[1]).resolve(), int(sys.argv[2])
    d = matt(sida, bredd)
    print("%s @ %d" % (sida.name, bredd))
    print(" storlekar (px: antal element):")
    for px in sorted(d["storlekar"], key=float, reverse=True):
        v = float(px)
        ut = "   <-- UTANFOR SKALAN" if (v != round(v) or round(v) not in SKALA) else ""
        print("   %7s : %3d%s" % (px, d["storlekar"][px], ut))
    print(" %d distinkta storlekar, huset har %d" % (len(d["storlekar"]), len(SKALA)))
    if "--element" in sys.argv:
        for e in d["element"]:
            print("   %-26s %6s/%-6s %-4s %s" % (str(e["k"])[:26], e["px"], e["lh"], e["w"], e["t"]))
