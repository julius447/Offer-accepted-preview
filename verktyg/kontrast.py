#!/usr/bin/env python3
"""Mäter textkontrast på en byggd sida.

    python3 verktyg/kontrast.py fall/laddbox.html

Komposerar alpha på riktigt: både textens rgba och varje genomskinligt
bakgrundslager läggs ner mot sidbasen #f5f9ff innan luminansen räknas.
En mätning som läser rgba(11,16,48,.62) som opakt #0b1030 ger 18:1 och
missar varje för ljus grå ton på sidan.

Kravet är WCAG AA: 4,5:1, eller 3,0:1 för text från 24 px, eller från
18,66 px i halvfet.
"""
import json, pathlib, re, subprocess, time, sys
HAR = pathlib.Path(".").resolve()
JS = r"""
<script>window.addEventListener('load',function(){
 function rgba(c){var m=(c||'').match(/[\d.]+/g);if(!m)return null;
  return [+m[0],+m[1],+m[2], m.length>3?+m[3]:1];}
 function over(f,b){var a=f[3];return [f[0]*a+b[0]*(1-a),f[1]*a+b[1]*(1-a),f[2]*a+b[2]*(1-a),1];}
 function lum(c){var a=c.slice(0,3).map(function(v){v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4);});
  return 0.2126*a[0]+0.7152*a[1]+0.0722*a[2];}
 var SIDBAS=[245,249,255,1];                 /* .oa background-color #f5f9ff */
 function bakgrund(e){var lager=[];var n=e;
  while(n&&n!==document.documentElement){var c=rgba(getComputedStyle(n).backgroundColor);
   if(c&&c[3]>0)lager.push(c);n=n.parentElement;}
  var b=SIDBAS;for(var i=lager.length-1;i>=0;i--)b=over(lager[i],b);return b;}
 var ut=[],sedda={};
 document.querySelectorAll('.oa__rad-pott,.oa__rad-text small,.oa__kvitto-not,.oa__fin,.oa__not,'
  +'.oa__prod span,.oa__ingar li span span,.oa__rad-pris--ord,.oa__step-text small,.oa__trust-item,'
  +'.oa__eyebrow,.oa__ref,.oa__contact,.oa__contact a,.oa__fin a,.oa__rad,.oa__title').forEach(function(e){
  var st=getComputedStyle(e);var bak=bakgrund(e);var fram=over(rgba(st.color),bak);
  var l1=lum(fram),l2=lum(bak);var k=(Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
  var namn=(e.className||e.tagName)+' '+st.fontSize+' '+st.fontWeight;
  if(!sedda[namn]){sedda[namn]=1;ut.push({sel:namn,kontrast:Math.round(k*100)/100});}});
 document.title='MATT'+JSON.stringify(ut);});</script>
"""
sida = pathlib.Path(sys.argv[1]).resolve()
prov = sida.parent/("_k-%d.html"%time.time_ns())
prov.write_text(sida.read_text(encoding="utf-8").replace("</body>", JS+"</body>"), encoding="utf-8")
prof = HAR/("_cr-%d"%time.time_ns())
r = subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome","--headless=new",
  "--disable-gpu","--no-sandbox","--allow-file-access-from-files","--user-data-dir="+str(prof),
  "--virtual-time-budget=9000","--window-size=900,1200","--dump-dom",prov.as_uri()],capture_output=True,timeout=120)
prov.unlink(missing_ok=True); subprocess.run(["rm","-rf",str(prof)],check=False)
import html as _h
m = re.search(r"<title>MATT(.*?)</title>", r.stdout.decode("utf-8","replace"), re.S)
for o in json.loads(_h.unescape(m.group(1))):
    px = float(re.search(r"([\d.]+)px", o["sel"]).group(1))
    vikt = int(o["sel"].split()[-1])
    krav = 3.0 if (px >= 24 or (px >= 18.66 and vikt >= 700)) else 4.5
    print("%-46s %5.2f  krav %.1f%s" % (o["sel"][:46], o["kontrast"], krav,
          "   <-- UNDER" if o["kontrast"] < krav else ""))
