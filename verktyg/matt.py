#!/usr/bin/env python3
"""Mäter en byggd sida i webbläsaren och skriver måtten som text.

    python3 verktyg/matt.py fall/laddbox.html 375

Mäter: sidledes scroll, element som sticker ut i bredd, träffytor under
44 x 44 px, antalet "kr" på sidan och finstiltens text. Ett mått är ett mått:
inget här är en bedömning.

Chrome klämmer fönsterbredden till 500 px på macOS (uppmätt: innerWidth 500
när --window-size sa 375), så den smala bredden måste komma ur en iframe i ett
bredare fönster. Innerdokumentet mäter sig själv och skriver resultatet i sin
egen <title>; ytterdokumentet pollar titeln och lyfter upp den, för en enda
setTimeout hann inte före dumpen.

Chrome körs med EGEN --user-data-dir och dödas med sin EGEN process-grupp.
Döda ALDRIG Chrome med pkill: det stänger användarens riktiga webbläsare.
"""
import html as _h, json, os, pathlib, re, signal, subprocess, sys, time

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
HAR = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sida = pathlib.Path(sys.argv[1]).resolve()
bredd = int(sys.argv[2])

MATT = """
<script>window.addEventListener('load',function(){
  var d=document.documentElement, ut={bredd:innerWidth,
    scrollWidth:d.scrollWidth, clientWidth:d.clientWidth,
    sidledes:d.scrollWidth-d.clientWidth, utanfor:[], smatraff:[]};
  document.querySelectorAll('.oa *').forEach(function(e){
    var r=e.getBoundingClientRect();
    if(r.width&&(r.left<-0.5||r.right>d.clientWidth+0.5))
      ut.utanfor.push((e.tagName+'.'+(e.className||'')).slice(0,60)+' '+Math.round(r.left)+'..'+Math.round(r.right));
  });
  document.querySelectorAll('.oa a,.oa button,.oa input,.oa summary').forEach(function(e){
    var r=e.getBoundingClientRect();
    if(r.height<44||r.width<44) ut.smatraff.push(e.tagName+' '+(e.textContent||'').trim().slice(0,24)+' '+Math.round(r.width)+'x'+Math.round(r.height));
  });
  var oa=document.querySelector('.oa');
  ut.fel=oa?oa.getAttribute('data-oa-fel'):null;
  ut.kr=(document.body.innerText.match(/kr/g)||[]).length;
  var f=document.getElementById('oaFin');
  ut.finstilt=(f&&!f.hidden)?f.textContent.trim():null;
  ut.hojd=document.querySelector('.oa__card').getBoundingClientRect().height;
  document.title='MATT'+JSON.stringify(ut);
});</script>
"""
inner = sida.parent / ("_matt-%d.html" % time.time_ns())
inner.write_text(sida.read_text(encoding="utf-8").replace("</body>", MATT + "</body>"), encoding="utf-8")
yttre = sida.parent / ("_yttre-%d.html" % time.time_ns())
yttre.write_text(
    '<!DOCTYPE html><meta charset="utf-8"><title>vantar</title>'
    '<style>html,body{margin:0}iframe{border:0;display:block}</style>'
    '<body><iframe id="f" src="%s" width="%d" height="2600"></iframe><script>'
    'var n=0,t=setInterval(function(){n++;try{var d=document.getElementById("f").contentDocument;'
    'if(d&&d.title.indexOf("MATT")===0){document.title=d.title;clearInterval(t);}}catch(e){}'
    'if(n>400)clearInterval(t);},20);</script></body>' % (inner.name, bredd), encoding="utf-8")

profil = HAR / ("_cr-%d" % time.time_ns())
cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
       "--allow-file-access-from-files", "--force-prefers-reduced-motion", "--hide-scrollbars",
       "--user-data-dir=" + str(profil), "--virtual-time-budget=12000",
       "--window-size=%d,1200" % (bredd + 80), "--dump-dom", yttre.as_uri()]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
try:
    out, _ = p.communicate(timeout=120)
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)      # BARA min egen grupp
    raise SystemExit("Chrome svarade inte")
inner.unlink(missing_ok=True); yttre.unlink(missing_ok=True)
subprocess.run(["rm", "-rf", str(profil)], check=False)
m = re.search(r"<title>MATT(.*?)</title>", out.decode("utf-8", "replace"), re.S)
if not m:
    raise SystemExit("inga matvarden tillbaka")
print(json.dumps(json.loads(_h.unescape(m.group(1))), ensure_ascii=False, indent=1))
