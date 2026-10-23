#!/usr/bin/env python3
"""Skärmbild av en byggd orderbekräftelse vid en ÄKTA bredd.

    python3 verktyg/skarmbild.py fall/laddbox.html 375 ut.png [höjd]

Chrome klämmer fönsterbredden till ungefär 500 px på macOS, så 375 måste komma
ur en iframe i ett bredare fönster. Samma grepp som laddboxrepots
gemensamt/verktyg/shot.py.

Chrome körs med EGEN --user-data-dir och dödas med sin EGEN process-grupp.
Döda ALDRIG Chrome med pkill: det stänger användarens riktiga webbläsare.
"""
import os, pathlib, signal, subprocess, sys, time

if len(sys.argv) < 4:
    raise SystemExit(__doc__)
HAR = pathlib.Path(__file__).resolve().parent.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
sida = pathlib.Path(sys.argv[1]).resolve()
bredd, ut = int(sys.argv[2]), pathlib.Path(sys.argv[3]).resolve()
hojd = int(sys.argv[4]) if len(sys.argv) > 4 else 2200

prov = HAR / ("_skarm-%d.html" % time.time_ns())
prov.write_text(
    '<!DOCTYPE html><meta charset="utf-8">'
    '<style>html,body{margin:0;background:#f5f9ff}iframe{border:0;display:block}</style>'
    '<body><iframe src="%s" width="%d" height="%d"></iframe></body>'
    % (sida.as_uri(), bredd, hojd), encoding="utf-8")
profil = HAR / ("_cr-%d" % time.time_ns())
ut.unlink(missing_ok=True)
cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
       "--allow-file-access-from-files", "--force-prefers-reduced-motion", "--hide-scrollbars",
       "--user-data-dir=" + str(profil), "--virtual-time-budget=8000",
       "--window-size=%d,%d" % (bredd + 24, hojd), "--screenshot=" + str(ut),
       prov.as_uri()]
p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
t0, forra = time.time(), -1
while time.time() - t0 < 70:
    if ut.exists():
        nu = ut.stat().st_size
        if nu > 0 and nu == forra:
            break
        forra = nu
    time.sleep(0.4)
try:
    os.killpg(os.getpgid(p.pid), signal.SIGKILL)      # BARA min egen grupp
except Exception:
    pass
prov.unlink(missing_ok=True)
subprocess.run(["rm", "-rf", str(profil)], check=False)
print(ut if ut.exists() else "ingen bild")
