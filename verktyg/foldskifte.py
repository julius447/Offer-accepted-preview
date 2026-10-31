#!/usr/bin/env python3
"""Mäter om kortets TOPP rör sig när en fold öppnas.

    python3 verktyg/foldskifte.py fall/laddbox.html 375 812
    python3 verktyg/foldskifte.py fall/laddbox.html 1180 800 --rorelse

ÄGARENS ORD 31 oktober, ordagrant: "Nu när jag trycker på t.ex villkor eller
någon av dropdownen är det som att allting expanderar över en, vilket gör att
man måste skrolla uppåt för att kunna läsa allt från toppen."

DET MÅTT SOM AVGÖR SAKEN är inte en känsla utan kortets topp i DOKUMENTET,
mätt vid scroll 0, före och efter att en fold öppnas. Rör den sig har allt
kunden tittade på glidit lika många pixlar, och sidans topp har hamnat
utanför vyporten. Står den still kan folden bara växa NEDÅT, vilket är det
enda en fold ska göra.

VARFÖR TOPPEN KAN RÖRA SIG. `.oa` är en kolumn med min-height:100dvh och
justify-content:center. Är kortet kortare än skärmen finns fri yta, och
centreringen lägger halva över kortet. Växer kortet krymper den fria ytan,
och toppen vandrar uppåt tills den tar slut. Centreringen är alltså inte
stillastående: den räknas om vid varje höjdändring.

Chrome klämmer fönsterbredden till 500 px på macOS, så den smala bredden
måste komma ur en iframe i ett bredare fönster — samma knep som matt.py.
IFRAMENS HÖJD ÄR VYPORTEN: 100dvh inne i en iframe är iframens höjd, och
utan den raden mäter provet en skärm som inte finns.

Chrome körs med EGEN --user-data-dir och dödas med sin EGEN process-grupp.
Döda ALDRIG Chrome med pkill: det stänger användarens riktiga webbläsare.
"""
import html as _h, json, os, pathlib, re, signal, subprocess, sys, time

if len(sys.argv) < 4:
    raise SystemExit(__doc__)
HAR = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sida = pathlib.Path(sys.argv[1]).resolve()
bredd = int(sys.argv[2])
hojd = int(sys.argv[3])
# Som standard mäts sidan med reducerad rörelse PÅ, precis som bygg.py
# renderar den. --rorelse mäter den som en kund med rörelse påslagen ser
# den, vilket är där animationerna faktiskt går.
rorelse = "--rorelse" in sys.argv
# --patch "<css>" skjuter in CSS SIST i sidan, sa en kandidatrattning kan
# matas utan att styles.css rors. Samma specificitet senare i dokumentet
# vinner, alltsa biter .oa{...} over husets egen rad.
patch = ""
for i, a in enumerate(sys.argv):
    if a == "--patch" and i + 1 < len(sys.argv):
        patch = sys.argv[i + 1]

MATT = """
<script>window.addEventListener('load',function(){
  var d=document.documentElement;
  var card=document.querySelector('.oa__card');
  var oa=document.querySelector('.oa');
  var folds=[].slice.call(document.querySelectorAll('.oa__fold'));
  function topp(){ scrollTo(0,0); return +card.getBoundingClientRect().top.toFixed(1); }
  function alla(v){ folds.forEach(function(f){ f.open=v; }); }

  alla(false);
  var cs=getComputedStyle(oa);
  var ut={ bredd:innerWidth, hojd:innerHeight,
    justify:cs.justifyContent, overflow:cs.overflowY,
    kortmarginal:getComputedStyle(card).marginTop+' / '+getComputedStyle(card).marginBottom,
    korthojd:+card.getBoundingClientRect().height.toFixed(1),
    toppStangd:topp(),
    scrollHojdStangd:d.scrollHeight, klientHojd:d.clientHeight,
    folder:[] };
  // FRI YTA = skärmen minus kortet. Finns den ska kortet vara centrerat,
  // och centreringen är det ägaren INTE klagar på: den ska bevaras.
  ut.friYtaStangd = +(innerHeight - ut.korthojd).toFixed(1);

  folds.forEach(function(f,i){
    alla(false);
    var t0=topp();
    f.open=true;
    var t1=topp();
    var sum=(f.querySelector('summary').textContent||'').trim().slice(0,38);
    ut.folder.push({ nr:i, namn:sum, toppStangd:t0, toppOppen:t1,
      skifte:+(t1-t0).toFixed(1),
      scrollHojdOppen:d.scrollHeight,
      kortTopOppenNegativ: t1 < -0.5 });
    f.open=false;
  });

  // ALLA FOLDER PÅ EN GÅNG: det värsta fallet, och det ägaren lätt gör.
  alla(false); var ta=topp();
  alla(true);  var tb=topp();
  ut.allaFolder={ toppStangd:ta, toppOppen:tb, skifte:+(tb-ta).toFixed(1),
                  korthojd:+card.getBoundingClientRect().height.toFixed(1),
                  scrollHojd:d.scrollHeight };
  alla(false);

  // ANIMATIONERNA: vad datorn FAKTISKT räknar, inte vad filen säger.
  function anim(sel){ var e=document.querySelector(sel); if(!e) return null;
    var c=getComputedStyle(e);
    return { namn:c.animationName, tid:c.animationDuration,
             iter:c.animationIterationCount, transition:c.transitionDuration }; }
  ut.rorelse={ reducerad:matchMedia('(prefers-reduced-motion: reduce)').matches,
    disc:anim('.oa__disc'), tick:anim('.oa__tick'), halo:anim('.oa__halo'),
    pil:anim('.oa__fold-pil') };

  document.title='MATT'+JSON.stringify(ut);
});</script>
"""
inner = sida.parent / ("_f-%d.html" % time.time_ns())
inner.write_text(sida.read_text(encoding="utf-8").replace(
    "</body>", ("<style>%s</style>" % patch if patch else "") + MATT + "</body>"),
                 encoding="utf-8")
yttre = sida.parent / ("_fy-%d.html" % time.time_ns())
yttre.write_text(
    '<!DOCTYPE html><meta charset="utf-8"><title>vantar</title>'
    '<style>html,body{margin:0}iframe{border:0;display:block}</style>'
    '<body><iframe id="f" src="%s" width="%d" height="%d"></iframe><script>'
    'var n=0,t=setInterval(function(){n++;try{var d=document.getElementById("f").contentDocument;'
    'if(d&&d.title.indexOf("MATT")===0){document.title=d.title;clearInterval(t);}}catch(e){}'
    'if(n>400)clearInterval(t);},20);</script></body>' % (inner.name, bredd, hojd),
    encoding="utf-8")

profil = HAR / ("_cr-%d" % time.time_ns())
cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
       "--allow-file-access-from-files", "--hide-scrollbars",
       "--user-data-dir=" + str(profil), "--virtual-time-budget=12000",
       "--window-size=%d,%d" % (bredd + 80, hojd + 120), "--dump-dom", yttre.as_uri()]
if not rorelse:
    cmd.insert(5, "--force-prefers-reduced-motion")
p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                     start_new_session=True)
try:
    out, _ = p.communicate(timeout=120)
except subprocess.TimeoutExpired:
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)      # BARA min egen grupp
    raise SystemExit("Chrome svarade inte")
finally:
    inner.unlink(missing_ok=True)
    yttre.unlink(missing_ok=True)
    subprocess.run(["rm", "-rf", str(profil)], check=False)
m = re.search(r"<title>MATT(.*?)</title>", out.decode("utf-8", "replace"), re.S)
if not m:
    raise SystemExit("inga matvarden tillbaka")
d = json.loads(_h.unescape(m.group(1)))
print(json.dumps(d, ensure_ascii=False, indent=1))
