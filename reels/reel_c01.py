import base64
import json
import subprocess
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
DUR = 25.0
W, H = 1080, 1920

spec = json.loads((ROOT / "specs/week1/c01_5to9.json").read_text())
chart = spec["slides"][3]["chart"]
solar = chart["lines"][0]["pts"]
home = chart["lines"][1]["pts"]
photo = base64.b64encode((ROOT / "photos/unsplash_benjamin-jopen_2SfssudtyIA.jpg").read_bytes()).decode()

SUN = '<svg width="44" height="44" viewBox="0 0 40 40"><circle cx="20" cy="20" r="8" fill="#F2B134"/><g stroke="#F2B134" stroke-width="3" stroke-linecap="round"><line x1="20" y1="3" x2="20" y2="8"/><line x1="20" y1="32" x2="20" y2="37"/><line x1="3" y1="20" x2="8" y2="20"/><line x1="32" y1="20" x2="37" y2="20"/><line x1="8" y1="8" x2="11.5" y2="11.5"/><line x1="28.5" y1="28.5" x2="32" y2="32"/><line x1="8" y1="32" x2="11.5" y2="28.5"/><line x1="28.5" y1="11.5" x2="32" y2="8"/></g></svg>'

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><style>
* { margin:0; padding:0; box-sizing:border-box; }
body { width:1080px; height:1920px; background:#14213D; font-family:Inter, sans-serif; color:#F6F1E7; overflow:hidden; }
.abs { position:absolute; left:90px; right:130px; }
.brand { top:200px; font-size:32px; font-weight:700; display:flex; align-items:center; gap:14px; }
.hook { top:600px; font-size:104px; line-height:1.04; font-weight:800; letter-spacing:-2px; }
.w { display:inline-block; opacity:0; }
.accent { color:#F2B134; }
.title { top:330px; font-size:68px; line-height:1.1; font-weight:800; letter-spacing:-1px; }
.big { top:640px; font-size:84px; line-height:1.1; font-weight:780; letter-spacing:-1.5px; }
.sub { font-size:58px; line-height:1.2; font-weight:700; margin-top:48px; }
.cap { top:1310px; font-size:44px; line-height:1.25; font-weight:650; }
.src { top:1500px; font-size:26px; line-height:1.35; opacity:0.6; font-weight:500; }
.bar { position:absolute; left:0; bottom:0; height:14px; background:#E07A1F; }
.legend { font-size:32px; font-weight:650; display:flex; gap:40px; margin-top:22px; }
.legend span { display:inline-flex; align-items:center; gap:12px; opacity:0; }
.photo { position:absolute; inset:0; background-size:cover; background-position:center; }
.shade { position:absolute; inset:0; background:linear-gradient(180deg, rgba(20,33,61,.5) 0%, rgba(20,33,61,.4) 30%, rgba(20,33,61,.75) 55%, rgba(20,33,61,.97) 80%); }
.cta-url { font-size:68px; font-weight:800; margin-top:44px; text-decoration:underline; text-decoration-color:#F2B134; text-decoration-thickness:6px; text-underline-offset:12px; }
</style></head><body>
<div id="s5" style="position:absolute;inset:0;opacity:0"><div id="ph" class="photo" style="background-image:url(data:image/jpeg;base64,PHOTO)"></div><div class="shade"></div>
  <div class="abs" style="top:900px"><div class="big" style="position:static">Follow for straight answers on Oʻahu solar.</div><div class="cta-url">@solarstraighttalk</div><div class="sub" style="font-size:44px;font-weight:600;opacity:.9">Free roof-by-roof math tool coming soon.</div></div>
</div>
<div class="abs brand">SUN Solar Straight Talk</div>
<div id="s1" class="abs hook"></div>
<div id="s2">
  <div id="t1" class="abs title" style="opacity:0">Panels peak at noon.</div>
  <div id="t2" class="abs title accent" style="top:410px;opacity:0">Homes peak after 5.</div>
  <div class="abs" style="top:580px;right:90px">
    <svg id="ch" width="900" height="620" viewBox="0 0 900 620"></svg>
    <div class="legend"><span id="lg1"><i style="width:44px;height:10px;border-radius:5px;background:#F2B134"></i>Solar output</span><span id="lg2"><i style="width:44px;height:10px;border-radius:5px;background:#F6F1E7"></i>Typical home use</span></div>
  </div>
  <div id="c1" class="abs cap" style="opacity:0">Midday, solar you send to the grid earns <span class="accent">13.5¢</span> per kWh.</div>
  <div id="c2" class="abs cap" style="opacity:0">5–9pm it earns <span class="accent">32.9¢</span>.<br>About 2½× the midday rate.</div>
</div>
<div id="s3" class="abs big" style="opacity:0"><div id="s3a">So the real question isn’t “how much do my panels make?”</div><div id="s3b" class="sub accent" style="opacity:0">It’s how much of it you use, and when.</div></div>
<div id="s4" class="abs big" style="opacity:0">That’s why system size and batteries change the value so much, house to house.</div>
<div id="src" class="abs src" style="opacity:0"></div>
<div id="bar" class="bar"></div>
<script>
const SOLAR = SOLARPTS, HOME = HOMEPTS;
const CW=900, CH=620, L=10, R=10, T=80, B=70, pw=CW-L-R, ph=CH-T-B;
const X = h => L + pw*h/24, Y = v => T + ph*(1-v);
const hx = (i,n) => 24*i/(n-1);
const pathOf = pts => pts.map((v,i)=>(i?'L':'M')+X(hx(i,pts.length)).toFixed(1)+','+Y(v).toFixed(1)).join(' ');
const svg = document.getElementById('ch');
svg.innerHTML = `
 <g id="ax"><line x1="${L}" y1="${T+ph}" x2="${L+pw}" y2="${T+ph}" stroke="#F6F1E7" stroke-opacity=".5" stroke-width="2"/>
 ${[[0,'12am','start'],[6,'6am','middle'],[12,'noon','middle'],[18,'6pm','middle'],[24,'12am','end']].map(([h,l,a])=>`<text x="${X(h)}" y="${T+ph+46}" fill="#F6F1E7" fill-opacity=".75" font-size="28" font-weight="600" text-anchor="${a}">${l}</text>`).join('')}</g>
 <g id="b1"><rect x="${X(9)}" y="${T}" width="${X(17)-X(9)}" height="${ph}" fill="#F6F1E7" opacity=".08"/><text id="n1" x="${(X(9)+X(17))/2}" y="${T-24}" fill="#F6F1E7" font-size="40" font-weight="800" text-anchor="middle"></text></g>
 <g id="b2"><rect x="${X(17)}" y="${T}" width="${X(21)-X(17)}" height="${ph}" fill="#F2B134" opacity=".22"/><text id="n2" x="${(X(17)+X(21))/2}" y="${T-24}" fill="#F2B134" font-size="40" font-weight="800" text-anchor="middle"></text></g>
 <path id="ps" d="${pathOf(SOLAR)}" fill="none" stroke="#F2B134" stroke-width="10" stroke-linejoin="round" stroke-linecap="round"/>
 <path id="ph2" d="${pathOf(HOME)}" fill="none" stroke="#F6F1E7" stroke-width="10" stroke-linejoin="round" stroke-linecap="round"/>
 <circle id="d1" r="14" fill="#F2B134"/><circle id="d2" r="14" fill="#F6F1E7"/>`;
const ps = document.getElementById('ps'), ph2 = document.getElementById('ph2');
const Ls = ps.getTotalLength(), Lh = ph2.getTotalLength();
ps.style.strokeDasharray = Ls; ph2.style.strokeDasharray = Lh;

const HOOK = ["Your","solar","panels","make","the","most","power","when","it’s","worth","the"];
document.getElementById('s1').innerHTML = HOOK.map(w=>`<span class="w">${w}</span>`).join(' ') + ' <span class="w accent" id="least">least.</span>';
const words = [...document.querySelectorAll('#s1 .w')];

const cl = v => Math.max(0, Math.min(1, v));
const seg = (t,a,b) => cl((t-a)/(b-a));
const ease = p => 1 - Math.pow(1-p, 3);
const io = p => p<.5 ? 4*p*p*p : 1-Math.pow(-2*p+2,3)/2;
const $ = id => document.getElementById(id);
function show(el, t, a, b, d=0.4, dy=40) {   // fade/slide in at a, out at b
  const pin = ease(seg(t, a, a+d)), pout = b==null ? 0 : ease(seg(t, b, b+d));
  el.style.opacity = pin*(1-pout);
  el.style.transform = `translateY(${(1-pin)*dy - pout*dy}px)`;
}
function setT(t) {
  // scene 1: hook
  words.forEach((w,i)=>{ const p = ease(seg(t, .15+i*.11, .45+i*.11)); w.style.opacity=p; w.style.transform=`translateY(${(1-p)*30}px)`; });
  const pl = seg(t, 1.6, 1.95), least = $('least');
  least.style.opacity = cl(pl*3); least.style.transform = `scale(${1.8 - .8*ease(pl)})`; least.style.transformOrigin='left center';
  const out1 = ease(seg(t, 3.0, 3.4)); $('s1').style.opacity = 1-out1; $('s1').style.transform=`translateY(${-80*out1}px)`;
  // scene 2: chart
  const s2out = ease(seg(t, 14.0, 14.5)); $('s2').style.opacity = 1-s2out;
  show($('t1'), t, 3.4, null); show($('t2'), t, 10.2, null);
  $('ax').style.opacity = ease(seg(t, 3.5, 3.9));
  const pS = io(seg(t, 3.9, 6.3)); ps.style.strokeDashoffset = Ls*(1-pS);
  const a = ps.getPointAtLength(Ls*pS); $('d1').setAttribute('cx',a.x); $('d1').setAttribute('cy',a.y); $('d1').style.opacity = (pS>0 && pS<1) ? 1 : 0;
  $('lg1').style.opacity = ease(seg(t, 3.9, 4.3));
  $('b1').style.opacity = ease(seg(t, 6.3, 6.7));
  $('n1').textContent = (13.5*ease(seg(t, 6.4, 7.4))).toFixed(1)+'¢';
  show($('c1'), t, 6.6, 10.6);
  const pH = io(seg(t, 8.4, 10.6)); ph2.style.strokeDashoffset = Lh*(1-pH);
  const b = ph2.getPointAtLength(Lh*pH); $('d2').setAttribute('cx',b.x); $('d2').setAttribute('cy',b.y); $('d2').style.opacity = (pH>0 && pH<1) ? 1 : 0;
  $('lg2').style.opacity = ease(seg(t, 8.4, 8.8));
  $('b2').style.opacity = ease(seg(t, 10.8, 11.2));
  $('n2').textContent = (32.9*ease(seg(t, 10.9, 11.9))).toFixed(1)+'¢';
  show($('c2'), t, 11.1, null);
  // scene 3
  show($('s3'), t, 14.5, 18.2, .5); show($('s3b'), t, 16.0, null, .5);
  // scene 4
  show($('s4'), t, 18.6, 21.4, .5);
  // scene 5: cta
  const p5 = ease(seg(t, 21.6, 22.2)); $('s5').style.opacity = p5; $('ph').style.transform = `scale(${1.12 - .1*seg(t,21.6,DUR)})`;
  // sources
  const src = $('src');
  if (t < 21.6) { src.innerHTML = 'Credit rates: Hawaiian Electric Rule 32 (Smart Export), Oʻahu, agreements signed Apr 2024–Apr 2027. Chart shapes illustrative.'; src.style.top='1500px'; show(src, t, 6.4, 21.0); src.style.opacity *= .6; }
  else { src.innerHTML = 'Not affiliated with Hawaiian Electric or any government agency. Photo: Benjamin Jopen / Unsplash.'; src.style.top='1560px'; src.style.opacity = .6*ease(seg(t,22.4,22.8)); src.style.transform='none'; }
  $('bar').style.width = (1080*t/DUR)+'px';
}
const DUR = DURV;
setT(0);
</script></body></html>"""

html = (HTML.replace("SUN", SUN).replace("SOLARPTS", json.dumps(solar)).replace("HOMEPTS", json.dumps(home))
        .replace("DURV", str(DUR)).replace("PHOTO", photo))

out_dir = ROOT / "rendered/reels"
frames = Path("/tmp/reel_frames")
frames.mkdir(exist_ok=True)
for f in frames.glob("*.jpg"):
    f.unlink()
only = [float(x) for x in sys.argv[1:]]  # optional: preview times
with sync_playwright() as p:
    br = p.chromium.launch(executable_path="/usr/bin/google-chrome")
    pg = br.new_page(viewport={"width": W, "height": H})
    pg.set_content(html)
    pg.wait_for_timeout(300)
    if only:
        for t in only:
            pg.evaluate(f"setT({t})")
            pg.screenshot(path=f"/tmp/preview_{t}.png")
        br.close()
        sys.exit()
    n = int(DUR * FPS)
    for i in range(n):
        pg.evaluate(f"setT({i / FPS})")
        pg.screenshot(path=str(frames / f"{i:05d}.jpg"), type="jpeg", quality=92)
    br.close()
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / "w1_c01_5to9_reel.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", str(frames / "%05d.jpg"),
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-shortest",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-movflags", "+faststart", str(out)], check=True)
print(out)
